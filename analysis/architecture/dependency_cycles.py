from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Set, Tuple


def _module_from_fqn(fqn: str) -> str:
    value = str(fqn or "").strip()
    if "." not in value:
        return value
    return value.rsplit(".", 1)[0]


def build_module_dependency_graph(resolved_calls: list, repo_prefix: str) -> dict:
    graph: Dict[str, Set[str]] = defaultdict(set)
    prefix = str(repo_prefix or "").strip()
    if not prefix:
        return {}

    for row in resolved_calls or []:
        if not isinstance(row, dict):
            continue
        caller_fqn = str(row.get("caller_fqn", "") or "").strip()
        callee_fqn = str(row.get("callee_fqn", "") or "").strip()
        if not caller_fqn or not callee_fqn:
            continue

        caller_module = _module_from_fqn(caller_fqn)
        callee_module = _module_from_fqn(callee_fqn)

        if not caller_module.startswith(prefix + "."):
            continue
        if not callee_module.startswith(prefix + "."):
            continue
        if caller_module == callee_module:
            continue
        graph[caller_module].add(callee_module)
        graph.setdefault(callee_module, set())

    return {k: set(v) for k, v in graph.items()}


def _normalize_cycle(cycle: List[str]) -> Tuple[str, ...]:
    # cycle is expected without duplicated closing node.
    if not cycle:
        return tuple()
    nodes = list(cycle)
    min_idx = min(range(len(nodes)), key=lambda i: nodes[i])
    rotated = nodes[min_idx:] + nodes[:min_idx]
    return tuple(rotated + [rotated[0]])


def find_dependency_cycles(graph: dict, max_cycles: int = 50, max_depth: int = 20) -> list:
    adjacency: Dict[str, List[str]] = {
        str(k): sorted(str(x) for x in (v or [])) for k, v in (graph or {}).items()
    }

    found: List[List[str]] = []
    seen: Set[Tuple[str, ...]] = set()

    def dfs(start: str, node: str, path: List[str], visited: Set[str]) -> None:
        if len(found) >= int(max_cycles):
            return
        if len(path) >= int(max_depth):
            return

        for nxt in adjacency.get(node, []):
            if nxt == start and len(path) >= 2:
                norm = _normalize_cycle(path)
                if norm and norm not in seen:
                    seen.add(norm)
                    found.append(list(norm))
                    if len(found) >= int(max_cycles):
                        return
                continue
            if nxt in visited:
                continue
            visited.add(nxt)
            path.append(nxt)
            dfs(start, nxt, path, visited)
            path.pop()
            visited.remove(nxt)

    for start in sorted(adjacency.keys()):
        dfs(start, start, [start], {start})
        if len(found) >= int(max_cycles):
            break

    return found[: int(max_cycles)]


def compute_dependency_cycle_metrics(resolved_calls: list, repo_prefix: str) -> dict:
    graph = build_module_dependency_graph(resolved_calls=resolved_calls, repo_prefix=repo_prefix)
    cycles = find_dependency_cycles(graph)
    edges = sum(len(v) for v in graph.values())
    return {
        "ok": True,
        "repo_prefix": str(repo_prefix or ""),
        "modules": len(graph),
        "edges": int(edges),
        "cycle_count": len(cycles),
        "cycles": cycles,
    }
