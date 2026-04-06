from __future__ import annotations

from collections import defaultdict
from typing import Dict, Any, Optional, Set
from analysis.graph.entrypoint_detector import detect_entry_points


def _kind_for_fqn(fqn: str, repo_prefix: str) -> str:
    value = str(fqn or "")
    if value.startswith("builtins."):
        return "builtin"
    if repo_prefix and (value == repo_prefix or value.startswith(repo_prefix + ".")):
        return "local"
    return "external"


def _symbol_locations(symbol_index) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    if symbol_index is None:
        return out
    try:
        symbols = symbol_index.all_symbols()
    except Exception:
        return out

    for sym in symbols:
        try:
            fqn = f"{sym.module}.{sym.qualified_name}"
            out[fqn] = {
                "file": str(getattr(sym, "file_path", "") or ""),
                "start_line": int(getattr(sym, "start_line", 1) or 1),
                "end_line": int(getattr(sym, "end_line", getattr(sym, "start_line", 1)) or 1),
            }
        except Exception:
            continue
    return out


def _infer_repo_prefix(nodes: Set[str]) -> str:
    counts: Dict[str, int] = defaultdict(int)
    for fqn in nodes:
        s = str(fqn or "")
        if not s or s.startswith("builtins."):
            continue
        first = s.split(".", 1)[0]
        if first:
            counts[first] += 1
    if not counts:
        return ""
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]


def compute_architecture_metrics(
    callgraph,
    symbol_index,
    repo_dir: Optional[str] = None,
    repo_prefix: Optional[str] = None,
    top_k: int = 25,
    fanout_threshold: int = 10,
    fanin_threshold: int = 10,
) -> dict:
    forward: Dict[str, Set[str]] = defaultdict(set)
    reverse: Dict[str, Set[str]] = defaultdict(set)
    all_nodes: Set[str] = set()

    try:
        callers = callgraph.all_callers()
    except Exception:
        callers = []

    for caller in callers:
        s = str(caller or "")
        all_nodes.add(s)
        for cs in callgraph.callees_of(s):
            callee = str(getattr(cs, "callee_fqn", "") or "")
            if not callee:
                continue
            forward[s].add(callee)
            reverse[callee].add(s)
            all_nodes.add(callee)

    locations = _symbol_locations(symbol_index)
    all_nodes.update(locations.keys())

    prefix = str(repo_prefix or "").strip() or _infer_repo_prefix(all_nodes)

    symbols_payload: Dict[str, Dict[str, Any]] = {}
    for fqn in sorted(all_nodes):
        loc = locations.get(fqn, {"file": "", "start_line": 1, "end_line": 1})
        symbols_payload[fqn] = {
            "fan_in": len(reverse.get(fqn, set())),
            "fan_out": len(forward.get(fqn, set())),
            "kind": _kind_for_fqn(fqn, prefix),
            "location": {
                "file": str(loc.get("file", "") or ""),
                "start_line": int(loc.get("start_line", 1) or 1),
                "end_line": int(loc.get("end_line", loc.get("start_line", 1)) or 1),
            },
        }

    locals_only = [f for f, s in symbols_payload.items() if s.get("kind") == "local"]
    dead_symbols = [f for f in locals_only if symbols_payload[f]["fan_in"] == 0 and not str(f).endswith(".<module>")]
    orchestrators = [f for f in locals_only if symbols_payload[f]["fan_out"] >= int(fanout_threshold)]
    critical = [f for f in locals_only if symbols_payload[f]["fan_in"] >= int(fanin_threshold)]

    top_fan_in = sorted(
        [{"fqn": f, "fan_in": symbols_payload[f]["fan_in"]} for f in symbols_payload],
        key=lambda r: (-int(r["fan_in"]), r["fqn"]),
    )[: int(top_k)]
    top_fan_out = sorted(
        [{"fqn": f, "fan_out": symbols_payload[f]["fan_out"]} for f in symbols_payload],
        key=lambda r: (-int(r["fan_out"]), r["fqn"]),
    )[: int(top_k)]

    files_payload: Dict[str, Dict[str, int]] = {}
    incoming_per_file: Dict[str, Set[str]] = defaultdict(set)
    outgoing_per_file: Dict[str, Set[str]] = defaultdict(set)
    edges_per_file: Dict[str, int] = defaultdict(int)

    for caller, callees in forward.items():
        caller_file = str(symbols_payload.get(caller, {}).get("location", {}).get("file", "") or "")
        if not caller_file:
            continue
        for callee in sorted(callees):
            callee_file = str(symbols_payload.get(callee, {}).get("location", {}).get("file", "") or "")
            outgoing_per_file[caller_file].add(caller)
            edges_per_file[caller_file] += 1
            if callee_file:
                incoming_per_file[callee_file].add(callee)

    all_files = set(incoming_per_file.keys()) | set(outgoing_per_file.keys()) | set(edges_per_file.keys())
    for fp in sorted(all_files):
        files_payload[fp] = {
            "incoming_symbols": len(incoming_per_file.get(fp, set())),
            "outgoing_symbols": len(outgoing_per_file.get(fp, set())),
            "edges": int(edges_per_file.get(fp, 0)),
        }

    entry_points = detect_entry_points(repo_dir=repo_dir, repo_prefix=prefix) if repo_dir else []

    return {
        "ok": True,
        "repo_prefix": prefix,
        "repo": {
            "total_nodes": len(symbols_payload),
            "dead_symbols": sorted(dead_symbols),
            "orchestrators": sorted(orchestrators),
            "critical_symbols": sorted(critical),
            "entry_points": entry_points,
            "top_fan_in": top_fan_in,
            "top_fan_out": top_fan_out,
        },
        "symbols": symbols_payload,
        "files": files_payload,
        "thresholds": {
            "fanout_threshold": int(fanout_threshold),
            "fanin_threshold": int(fanin_threshold),
            "top_k": int(top_k),
        },
    }
