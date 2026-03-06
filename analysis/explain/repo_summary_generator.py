from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Tuple


def _load_json(path: str, default: Any) -> Any:
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _save_json(path: str, payload: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def _short_loc(symbol_meta: Dict[str, Any]) -> Tuple[str, int]:
    loc = symbol_meta.get("location", {}) if isinstance(symbol_meta.get("location"), dict) else {}
    return str(loc.get("file", "") or ""), int(loc.get("start_line", 1) or 1)


def build_repo_summary_context(repo_cache_dir: str) -> dict:
    arch = _load_json(os.path.join(repo_cache_dir, "architecture_metrics.json"), {})
    dep = _load_json(os.path.join(repo_cache_dir, "dependency_cycles.json"), {})
    analysis = _load_json(os.path.join(repo_cache_dir, "analysis_metrics.json"), {})
    tree = _load_json(os.path.join(repo_cache_dir, "project_tree.json"), {})
    risk = _load_json(os.path.join(repo_cache_dir, "risk_radar.json"), {})

    repo = arch.get("repo", {}) if isinstance(arch.get("repo"), dict) else {}
    symbols = arch.get("symbols", {}) if isinstance(arch.get("symbols"), dict) else {}

    orchestrators = [str(x) for x in (repo.get("orchestrators") or [])][:5]
    critical = [str(x) for x in (repo.get("critical_symbols") or [])][:5]

    def _shape(items: List[str]) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for fqn in items:
            meta = symbols.get(fqn, {}) if isinstance(symbols.get(fqn), dict) else {}
            file_path, line = _short_loc(meta)
            out.append(
                {
                    "fqn": fqn,
                    "in": int(meta.get("fan_in", 0) or 0),
                    "out": int(meta.get("fan_out", 0) or 0),
                    "file": file_path,
                    "line": line,
                }
            )
        return out

    top_hotspots = risk.get("top_hotspots", []) if isinstance(risk.get("top_hotspots"), list) else []
    return {
        "repo_prefix": str(arch.get("repo_prefix", "") or ""),
        "counts": {
            "symbols": int(len(symbols)),
            "calls": int(analysis.get("total_calls", 0) or 0),
            "files": int(analysis.get("total_files", 0) or 0),
            "unresolved_calls": int(analysis.get("unresolved_calls", 0) or 0),
            "cycles_count": int(dep.get("cycle_count", 0) or 0),
        },
        "orchestrators": _shape(orchestrators),
        "critical_apis": _shape(critical),
        "dead_symbols": [str(x) for x in (repo.get("dead_symbols") or [])][:10],
        "cycles": dep.get("cycles", [])[:5] if isinstance(dep.get("cycles"), list) else [],
        "top_tree_entries": tree.get("children", [])[:10] if isinstance(tree, dict) else [],
        "top_hotspots": top_hotspots[:5],
    }


def _normalize_summary(summary: Dict[str, Any]) -> Dict[str, Any]:
    bullets = [str(x).strip() for x in (summary.get("bullets") or []) if str(x).strip()][:7]
    one = str(summary.get("one_liner", "") or "").strip() or (bullets[0] if bullets else "Repository summary unavailable.")
    notes = [str(x).strip() for x in (summary.get("notes") or []) if str(x).strip()][:5]
    return {"one_liner": one[:180], "bullets": bullets, "notes": notes}


def _deterministic_summary(context: Dict[str, Any]) -> Dict[str, Any]:
    counts = context.get("counts", {}) if isinstance(context.get("counts"), dict) else {}
    files = int(counts.get("files", 0) or 0)
    symbols = int(counts.get("symbols", 0) or 0)
    calls = int(counts.get("calls", 0) or 0)
    cycles_count = int(counts.get("cycles_count", 0) or 0)
    unresolved = int(counts.get("unresolved_calls", 0) or 0)
    orchestrators = context.get("orchestrators", []) if isinstance(context.get("orchestrators"), list) else []
    critical = context.get("critical_apis", []) if isinstance(context.get("critical_apis"), list) else []
    dead = context.get("dead_symbols", []) if isinstance(context.get("dead_symbols"), list) else []
    hotspots = context.get("top_hotspots", []) if isinstance(context.get("top_hotspots"), list) else []

    top_orchestrators = [str(item.get("fqn", "") or "") for item in orchestrators[:3] if isinstance(item, dict)]
    top_critical = [str(item.get("fqn", "") or "") for item in critical[:3] if isinstance(item, dict)]
    top_hotspot_labels = []
    for item in hotspots[:3]:
        if isinstance(item, dict):
            top_hotspot_labels.append(str(item.get("fqn") or item.get("file") or "").strip())
        elif isinstance(item, str):
            top_hotspot_labels.append(item)
    one_liner = f"Scanned {files} files, indexed {symbols} symbols, and resolved {calls} calls."
    bullets: List[str] = []
    if top_orchestrators:
        bullets.append("Top orchestrators: " + ", ".join(top_orchestrators))
    if top_critical:
        bullets.append("Critical APIs: " + ", ".join(top_critical))
    bullets.append(f"Dependency cycles: {cycles_count}")
    if top_hotspot_labels:
        bullets.append("Hotspots: " + ", ".join(top_hotspot_labels))
    if unresolved:
        bullets.append(f"Unresolved calls: {unresolved}")
    if dead:
        bullets.append("Dead symbols: " + ", ".join([str(x) for x in dead[:3]]))
    if not bullets:
        bullets.append("No major hotspots detected from cached architecture artifacts.")
    notes = []
    if cycles_count:
        notes.append("Break dependency cycles first to reduce architecture friction.")
    if hotspots:
        notes.append("Review top hotspots before making broad refactors.")
    return _normalize_summary({"one_liner": one_liner, "bullets": bullets, "notes": notes})


def generate_repo_summary(repo_cache_dir: str, llm_client=None) -> dict:
    context = build_repo_summary_context(repo_cache_dir)
    summary = _deterministic_summary(context)
    payload = {
        "ok": True,
        "cached": False,
        "provider": "deterministic",
        "summary": summary,
        "error": None,
    }
    _save_json(os.path.join(repo_cache_dir, "repo_summary.json"), payload)
    return payload
