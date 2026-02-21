from __future__ import annotations

import hashlib
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

    context = {
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
    }

    # Keep payload small.
    compact = json.dumps(context, ensure_ascii=True)
    if len(compact.encode("utf-8")) > 4096:
        context["top_tree_entries"] = []
        context["dead_symbols"] = context["dead_symbols"][:5]
    return context


def _cache_key(context: Dict[str, Any], prompt_version: str = "repo_summary_v1") -> str:
    blob = json.dumps({"v": prompt_version, "context": context}, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _normalize_summary(text: str) -> Dict[str, Any]:
    raw_lines = [ln.strip() for ln in str(text or "").splitlines() if ln.strip()]
    lines: List[str] = []
    for ln in raw_lines:
        if ln.startswith("###"):
            ln = ln.lstrip("# ")
        if ln.lower().startswith("architecture explanation"):
            continue
        if not ln.startswith("-"):
            ln = f"- {ln}"
        lines.append(ln)
    if not lines:
        lines = ["- Repository summary unavailable."]
    lines = lines[:7]
    one = lines[0].lstrip("- ") if lines else "Repository summary unavailable."
    bullets = [ln.lstrip("- ")[:120] for ln in lines[:7]]
    return {"one_liner": one[:140], "bullets": bullets, "notes": []}


def generate_repo_summary(repo_cache_dir: str, llm_client) -> dict:
    context = build_repo_summary_context(repo_cache_dir)
    key = _cache_key(context)

    llm_cache_path = os.path.join(repo_cache_dir, "llm_cache.json")
    llm_cache = _load_json(llm_cache_path, {})
    if not isinstance(llm_cache, dict):
        llm_cache = {}

    cache_ns = f"repo_summary:{key}"
    cached = llm_cache.get(cache_ns)
    if isinstance(cached, dict):
        summary = cached.get("summary", {}) if isinstance(cached.get("summary"), dict) else {}
        return {
            "ok": True,
            "cached": True,
            "provider": str(cached.get("provider", "") or ""),
            "summary": summary,
            "error": None,
        }

    prompt = (
        "Give a concise repository architecture summary in plain text bullets (max 7 bullets).\n"
        "Mention code style (script vs library), orchestration entrypoints, and key hotspots/cycles.\n"
        "No markdown headings.\n\n"
        f"Context JSON:\n{json.dumps(context, ensure_ascii=True)}"
    )

    ai_result = llm_client.complete_text(prompt)
    if not isinstance(ai_result, dict) or not ai_result.get("ok"):
        return {
            "ok": False,
            "cached": False,
            "provider": str((ai_result or {}).get("provider", "") if isinstance(ai_result, dict) else ""),
            "summary": {},
            "error": (ai_result or {}).get("error", "AI generation failed") if isinstance(ai_result, dict) else "AI generation failed",
        }

    summary = _normalize_summary(str(ai_result.get("text", "") or ""))
    summary["top_orchestrators"] = context.get("orchestrators", [])[:5]
    summary["critical_apis"] = context.get("critical_apis", [])[:5]
    summary["dependency_cycles"] = [
        {"cycle": c, "kind": "module"} for c in (context.get("cycles", []) if isinstance(context.get("cycles"), list) else [])
    ][:5]

    llm_cache[cache_ns] = {
        "provider": str(ai_result.get("provider", "") or ""),
        "model": str(ai_result.get("model", "") or ""),
        "summary": summary,
    }
    _save_json(llm_cache_path, llm_cache)

    return {
        "ok": True,
        "cached": False,
        "provider": str(ai_result.get("provider", "") or ""),
        "summary": summary,
        "error": None,
    }
