from __future__ import annotations

import json
import os
from collections import defaultdict, deque
from typing import Any, Dict, List, Optional, Set, Tuple


def _load_json(path: str, default: Any) -> Any:
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def load_resolved_calls(cache_dir: str) -> List[dict]:
    data = _load_json(os.path.join(cache_dir, "resolved_calls.json"), [])
    return data if isinstance(data, list) else []


def build_adjacency(resolved_calls: List[dict]) -> Tuple[Dict[str, Set[str]], Dict[str, Set[str]]]:
    forward: Dict[str, Set[str]] = defaultdict(set)
    backward: Dict[str, Set[str]] = defaultdict(set)
    for row in resolved_calls:
        if not isinstance(row, dict):
            continue
        caller = str(row.get("caller_fqn", "") or "")
        callee = str(row.get("callee_fqn", "") or "")
        if not caller or not callee:
            continue
        forward[caller].add(callee)
        backward[callee].add(caller)
        forward.setdefault(callee, set())
        backward.setdefault(caller, set())
    return forward, backward


def infer_repo_prefix(cache_dir: str) -> str:
    arch = _load_json(os.path.join(cache_dir, "architecture_metrics.json"), {})
    if isinstance(arch, dict):
        prefix = str(arch.get("repo_prefix", "") or "")
        if prefix:
            return prefix
    return ""


def resolve_target(target: str, repo_prefix: str, resolved_calls: List[dict], arch_metrics: Dict[str, Any]) -> Dict[str, Any]:
    raw = str(target or "").strip()
    if not raw:
        return {"type": "symbol", "value": "", "start_nodes": []}

    if "." in raw:
        return {"type": "symbol", "value": raw, "start_nodes": [raw]}

    match_suffix = raw.replace("\\", "/")
    start_nodes: Set[str] = set()
    for row in resolved_calls:
        if not isinstance(row, dict):
            continue
        file_path = str(row.get("file", "") or "").replace("\\", "/")
        if file_path.endswith(match_suffix):
            caller = str(row.get("caller_fqn", "") or "")
            if caller:
                start_nodes.add(caller)

    if not start_nodes and repo_prefix:
        symbols = arch_metrics.get("symbols", {}) if isinstance(arch_metrics, dict) else {}
        for fqn, meta in (symbols.items() if isinstance(symbols, dict) else []):
            if not isinstance(meta, dict):
                continue
            loc = meta.get("location", {}) if isinstance(meta.get("location"), dict) else {}
            file_path = str(loc.get("file", "") or "").replace("\\", "/")
            if file_path.endswith(match_suffix):
                start_nodes.add(str(fqn))

    return {"type": "file", "value": raw, "start_nodes": sorted(start_nodes)}


def _node_details(
    fqn: str,
    symbols: Dict[str, Any],
    resolved_calls: List[dict],
) -> Dict[str, Any]:
    sym = symbols.get(fqn, {}) if isinstance(symbols, dict) and isinstance(symbols.get(fqn), dict) else {}
    fan_in = int(sym.get("fan_in", 0) or 0)
    fan_out = int(sym.get("fan_out", 0) or 0)
    loc = sym.get("location", {}) if isinstance(sym.get("location"), dict) else {}
    file_path = str(loc.get("file", "") or "")
    line = int(loc.get("start_line", 1) or 1)

    if not file_path:
        for row in resolved_calls:
            if not isinstance(row, dict):
                continue
            if str(row.get("caller_fqn", "") or "") == fqn or str(row.get("callee_fqn", "") or "") == fqn:
                file_path = str(row.get("file", "") or "")
                line = int(row.get("line", 1) or 1)
                break

    return {
        "fqn": fqn,
        "fan_in": fan_in,
        "fan_out": fan_out,
        "file": file_path,
        "line": line,
    }


def _bfs(
    starts: List[str],
    adjacency: Dict[str, Set[str]],
    depth: int,
    max_nodes: int,
) -> Tuple[Dict[str, int], List[Dict[str, str]], bool]:
    visited_dist: Dict[str, int] = {}
    edges: List[Dict[str, str]] = []
    truncated = False

    q: deque[Tuple[str, int]] = deque()
    for s in starts:
        q.append((s, 0))

    while q:
        node, dist = q.popleft()
        if dist >= depth:
            continue
        neighbors = sorted(adjacency.get(node, set()))
        for nxt in neighbors:
            edges.append({"from": node, "to": nxt})
            next_dist = dist + 1
            prev = visited_dist.get(nxt)
            if prev is None or next_dist < prev:
                if len(visited_dist) >= max_nodes:
                    truncated = True
                    continue
                visited_dist[nxt] = next_dist
                q.append((nxt, next_dist))

    return visited_dist, edges, truncated


def summarize_impacted_files(nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    counts: Dict[str, int] = defaultdict(int)
    for n in nodes:
        file_path = str(n.get("file", "") or "")
        if file_path:
            counts[file_path] += 1
    rows = [{"file": f, "count": c} for f, c in counts.items()]
    rows.sort(key=lambda r: (-int(r["count"]), r["file"]))
    return rows


def compute_impact(cache_dir: str, target: str, depth: int = 2, max_nodes: int = 200) -> dict:
    depth = max(1, int(depth))
    max_nodes = max(10, int(max_nodes))

    resolved_calls = load_resolved_calls(cache_dir)
    arch = _load_json(os.path.join(cache_dir, "architecture_metrics.json"), {})
    if not isinstance(arch, dict):
        arch = {}

    repo_prefix = infer_repo_prefix(cache_dir)
    symbols = arch.get("symbols", {}) if isinstance(arch.get("symbols"), dict) else {}
    forward, backward = build_adjacency(resolved_calls)

    target_info = resolve_target(target=target, repo_prefix=repo_prefix, resolved_calls=resolved_calls, arch_metrics=arch)
    starts = [str(s) for s in (target_info.get("start_nodes") or []) if str(s)]

    up_map, up_edges_raw, up_trunc = _bfs(starts=starts, adjacency=backward, depth=depth, max_nodes=max_nodes)
    down_map, down_edges_raw, down_trunc = _bfs(starts=starts, adjacency=forward, depth=depth, max_nodes=max_nodes)

    upstream_nodes = []
    for fqn, dist in sorted(up_map.items(), key=lambda kv: (kv[1], kv[0])):
        row = _node_details(fqn, symbols, resolved_calls)
        row["distance"] = int(dist)
        upstream_nodes.append(row)

    downstream_nodes = []
    for fqn, dist in sorted(down_map.items(), key=lambda kv: (kv[1], kv[0])):
        row = _node_details(fqn, symbols, resolved_calls)
        row["distance"] = int(dist)
        downstream_nodes.append(row)

    upstream_edges = [{"from": e["to"], "to": e["from"]} for e in up_edges_raw]
    downstream_edges = list(down_edges_raw)

    return {
        "ok": True,
        "repo_prefix": repo_prefix,
        "target": {"type": target_info.get("type", "symbol"), "value": str(target_info.get("value", "") or "")},
        "depth": depth,
        "max_nodes": max_nodes,
        "upstream": {
            "nodes": upstream_nodes,
            "edges": upstream_edges,
            "truncated": bool(up_trunc),
        },
        "downstream": {
            "nodes": downstream_nodes,
            "edges": downstream_edges,
            "truncated": bool(down_trunc),
        },
        "impacted_files": {
            "upstream": summarize_impacted_files(upstream_nodes),
            "downstream": summarize_impacted_files(downstream_nodes),
        },
    }
