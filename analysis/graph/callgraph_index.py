# Build caller->callees and reverse index
# analysis/graph/callgraph_index.py

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from collections import Counter
from typing import Dict, List, Optional, Set, Any


@dataclass(frozen=True)
class CallSite:
    caller_fqn: str
    callee_fqn: Optional[str]
    callee_name: str
    file: str
    line: int


class CallGraphIndex:
    """Stores forward/reverse call indexes and unresolved call list."""

    def __init__(self):
        self._forward: Dict[str, List[CallSite]] = {}
        self._reverse: Dict[str, List[CallSite]] = {}
        self._unresolved: List[CallSite] = []

    def add_call(self, callsite: CallSite) -> None:
        self._forward.setdefault(callsite.caller_fqn, []).append(callsite)
        if callsite.callee_fqn:
            self._reverse.setdefault(callsite.callee_fqn, []).append(callsite)
        else:
            self._unresolved.append(callsite)

    def callees_of(self, caller_fqn: str) -> List[CallSite]:
        return self._forward.get(caller_fqn, [])

    def callers_of(self, callee_fqn: str) -> List[CallSite]:
        return self._reverse.get(callee_fqn, [])

    def unresolved_calls(self) -> List[CallSite]:
        return list(self._unresolved)

    def all_callers(self) -> List[str]:
        return sorted(self._forward.keys())

    def all_callees(self) -> List[str]:
        return sorted(self._reverse.keys())

    def stats(self) -> dict:
        return {
            "unique_callers": len(self._forward),
            "unique_callees": len(self._reverse),
            "unresolved_calls": len(self._unresolved),
            "total_calls": sum(len(v) for v in self._forward.values()),
        }


def build_caller_fqn(call: dict, current_module: str) -> str:
    caller = call.get("caller", "<unknown>")
    cls = call.get("class")
    if cls:
        return f"{current_module}.{cls}.{caller}"
    return f"{current_module}.{caller}"


def write_hub_metrics_from_resolved_calls(resolved_calls_path: str, output_path: Optional[str] = None) -> Dict[str, Any]:
    """Compute simple repository call metrics from resolved_calls.json and optionally write to file."""
    if not os.path.exists(resolved_calls_path):
        raise FileNotFoundError(resolved_calls_path)

    with open(resolved_calls_path, "r", encoding="utf-8") as f:
        rows = json.load(f)
    if not isinstance(rows, list):
        rows = []

    fan_in: Counter[str] = Counter()
    fan_out: Counter[str] = Counter()
    files: Set[str] = set()
    unresolved = 0

    for row in rows:
        if not isinstance(row, dict):
            continue
        caller = str(row.get("caller_fqn", "") or "")
        callee = str(row.get("callee_fqn", "") or "")
        file_path = str(row.get("file", "") or "")
        if file_path:
            files.add(file_path)

        if caller:
            fan_out[caller] += 1
        if callee:
            fan_in[callee] += 1
        else:
            unresolved += 1

    critical_apis = [{"fqn": fqn, "fan_in": cnt} for fqn, cnt in fan_in.most_common(25)]
    orchestrators = [{"fqn": fqn, "fan_out": cnt} for fqn, cnt in fan_out.most_common(25)]

    payload: Dict[str, Any] = {
        "ok": True,
        "total_calls": len(rows),
        "unresolved_calls": unresolved,
        "total_files": len(files),
        "critical_apis": critical_apis,
        "orchestrators": orchestrators,
    }

    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

    return payload
