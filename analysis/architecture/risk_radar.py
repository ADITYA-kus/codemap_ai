from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List


def _load_json(path: str, default: Any) -> Any:
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _percentile_90(values: List[int], floor: int) -> int:
    vals = sorted(int(v) for v in values if int(v) >= 0)
    if not vals:
        return int(floor)
    idx = int(0.9 * (len(vals) - 1))
    return max(int(floor), int(vals[idx]))


def _risk_label(score: int) -> str:
    if score >= 70:
        return "high"
    if score >= 40:
        return "medium"
    return "low"


def _clamp(value: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, int(value)))


def compute_risk_radar(cache_dir: str, top_k: int = 25) -> dict:
    arch = _load_json(os.path.join(cache_dir, "architecture_metrics.json"), {})
    dep = _load_json(os.path.join(cache_dir, "dependency_cycles.json"), {})
    analysis = _load_json(os.path.join(cache_dir, "analysis_metrics.json"), {})

    if not isinstance(arch, dict) or not arch:
        raise RuntimeError("Missing architecture_metrics.json")

    repo_prefix = str(arch.get("repo_prefix", "") or "")
    repo = arch.get("repo", {}) if isinstance(arch.get("repo"), dict) else {}
    symbols = arch.get("symbols", {}) if isinstance(arch.get("symbols"), dict) else {}
    files = arch.get("files", {}) if isinstance(arch.get("files"), dict) else {}

    local_symbols = {fqn: s for fqn, s in symbols.items() if isinstance(s, dict) and str(s.get("kind", "")) == "local"}
    fan_in_vals = [int(s.get("fan_in", 0) or 0) for s in local_symbols.values()]
    fan_out_vals = [int(s.get("fan_out", 0) or 0) for s in local_symbols.values()]
    file_edges_vals = [int((v or {}).get("edges", 0) or 0) for v in files.values() if isinstance(v, dict)]

    fan_in_hot = _percentile_90(fan_in_vals, 10)
    fan_out_hot = _percentile_90(fan_out_vals, 10)
    file_edges_hot = _percentile_90(file_edges_vals, 20)

    total_calls = int(analysis.get("total_calls", 0) or 0)
    unresolved_calls = int(analysis.get("unresolved_calls", 0) or 0)
    unresolved_ratio = float(unresolved_calls / total_calls) if total_calls > 0 else 0.0
    cycle_count = int(dep.get("cycle_count", 0) or 0)

    orchestrators = set(str(x) for x in (repo.get("orchestrators") or []))
    critical = set(str(x) for x in (repo.get("critical_symbols") or []))

    hotspots: List[Dict[str, Any]] = []
    for fqn, sym in local_symbols.items():
        fan_in = int(sym.get("fan_in", 0) or 0)
        fan_out = int(sym.get("fan_out", 0) or 0)
        score = 0
        reasons: List[str] = []
        flags: List[str] = []

        if fan_in >= fan_in_hot:
            score += 40
            reasons.append("High fan-in: many callers depend on it")
        if fan_out >= fan_out_hot:
            score += 40
            reasons.append("High fan-out: orchestrates many calls")
        if fqn in orchestrators:
            score += 15
            flags.append("orchestrator")
        if fqn in critical:
            score += 15
            flags.append("critical")
        if str(fqn).endswith(".<module>"):
            score += 10
            reasons.append("Module-level script orchestration")
            flags.append("module_level")
        if cycle_count > 0:
            score += 10
            reasons.append("Repo has dependency cycles")
            flags.append("cycle_related")
        if unresolved_ratio > 0.2:
            score += 10
            reasons.append("High unresolved call ratio")

        score = _clamp(score, 0, 100)
        loc = sym.get("location", {}) if isinstance(sym.get("location"), dict) else {}
        hotspots.append(
            {
                "fqn": fqn,
                "risk": _risk_label(score),
                "score": score,
                "reasons": reasons,
                "fan_in": fan_in,
                "fan_out": fan_out,
                "location": {
                    "file": str(loc.get("file", "") or ""),
                    "start_line": int(loc.get("start_line", 1) or 1),
                    "end_line": int(loc.get("end_line", loc.get("start_line", 1)) or 1),
                },
                "flags": sorted(set(flags)),
            }
        )

    hotspots = sorted(hotspots, key=lambda h: (-int(h["score"]), h["fqn"]))[: int(top_k)]

    file_out_vals = sorted([int((v or {}).get("outgoing_symbols", 0) or 0) for v in files.values() if isinstance(v, dict)])
    file_in_vals = sorted([int((v or {}).get("incoming_symbols", 0) or 0) for v in files.values() if isinstance(v, dict)])
    out_top = file_out_vals[int(0.9 * (len(file_out_vals) - 1))] if file_out_vals else 0
    in_top = file_in_vals[int(0.9 * (len(file_in_vals) - 1))] if file_in_vals else 0

    risky_files: List[Dict[str, Any]] = []
    for file_path, fv in files.items():
        if not isinstance(fv, dict):
            continue
        edges = int(fv.get("edges", 0) or 0)
        incoming = int(fv.get("incoming_symbols", 0) or 0)
        outgoing = int(fv.get("outgoing_symbols", 0) or 0)

        score = 0
        reasons: List[str] = []
        if edges >= file_edges_hot:
            score += 60
            reasons.append("High edge density")
        if outgoing >= out_top and out_top > 0:
            score += 20
            reasons.append("Top outgoing coupling")
        if incoming >= in_top and in_top > 0:
            score += 20
            reasons.append("Top incoming coupling")

        score = _clamp(score, 0, 100)
        risky_files.append(
            {
                "file": str(file_path),
                "risk": _risk_label(score),
                "score": score,
                "edges": edges,
                "incoming_symbols": incoming,
                "outgoing_symbols": outgoing,
                "reasons": reasons,
            }
        )

    risky_files = sorted(risky_files, key=lambda r: (-int(r["score"]), r["file"]))[: int(top_k)]

    by_fan_out = sorted(hotspots, key=lambda h: (-int(h.get("fan_out", 0)), h["fqn"]))
    by_fan_in = sorted(hotspots, key=lambda h: (-int(h.get("fan_in", 0)), h["fqn"]))
    module_level = [h for h in hotspots if "module_level" in (h.get("flags") or [])]

    refactor_targets: List[Dict[str, Any]] = []
    if by_fan_out:
        refactor_targets.append({
            "title": "Break down top orchestrator",
            "why": "High fan-out symbols coordinate too many responsibilities.",
            "targets": [h["fqn"] for h in by_fan_out[:3]],
        })
    if by_fan_in:
        refactor_targets.append({
            "title": "Stabilize critical API",
            "why": "High fan-in symbols affect many callers and should remain stable.",
            "targets": [h["fqn"] for h in by_fan_in[:3]],
        })
    if module_level:
        refactor_targets.append({
            "title": "Reduce script-level work",
            "why": "Module-level orchestration is harder to test and reuse.",
            "targets": [h["fqn"] for h in module_level[:3]],
        })
    if unresolved_ratio > 0.2:
        refactor_targets.append({
            "title": "Investigate unresolved calls",
            "why": "Unresolved calls hide dependencies and increase uncertainty.",
            "targets": [f"unresolved_ratio={unresolved_ratio:.2f}"],
        })
    if cycle_count > 0:
        cycle_preview = dep.get("cycles", []) if isinstance(dep.get("cycles"), list) else []
        pretty = [" -> ".join(str(x) for x in c) for c in cycle_preview[:3] if isinstance(c, list)]
        refactor_targets.append({
            "title": "Address dependency cycles",
            "why": "Cycles increase coupling and make changes risky.",
            "targets": pretty,
        })

    return {
        "ok": True,
        "repo_prefix": repo_prefix,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "thresholds": {
            "fan_in_hot": int(fan_in_hot),
            "fan_out_hot": int(fan_out_hot),
            "file_edges_hot": int(file_edges_hot),
            "top_k": int(top_k),
        },
        "repo_health": {
            "hotspot_symbols": len(hotspots),
            "risky_files": len(risky_files),
            "dead_symbols": len(repo.get("dead_symbols", []) if isinstance(repo.get("dead_symbols"), list) else []),
            "dependency_cycles": cycle_count,
            "unresolved_ratio": round(unresolved_ratio, 6),
        },
        "hotspots": hotspots,
        "risky_files": risky_files,
        "refactor_targets": refactor_targets[:6],
    }
