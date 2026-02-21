"""
Manual verification for Phase-5 Step-1 (CallGraphIndex)

This file:
- loads Phase-4 output (resolved_calls.json)
- builds CallGraphIndex
- prints callers / callees for sanity checking

NOT used by core pipeline.
Safe to delete anytime.
"""

import json
import os

from analysis.graph.callgraph_index import CallGraphIndex, CallSite

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))  # project root
print("PROJECRT",PROJECT_ROOT)
RESOLVED_CALLS_JSON = os.path.join(
    PROJECT_ROOT, "code_assist_phase2","analysis","output", "resolved_calls.json"
)


def build_index(resolved_calls: list[dict]) -> CallGraphIndex:
    idx = CallGraphIndex()

    for c in resolved_calls:
        callsite = CallSite(
            caller_fqn=c["caller_fqn"],
            callee_fqn=c.get("callee_fqn"),
            callee_name=c.get("callee", "<unknown>"),
            file=c.get("file", ""),
            line=int(c.get("line", -1)),
        )
        idx.add_call(callsite)

    return idx


def main():
    if not os.path.exists(RESOLVED_CALLS_JSON):
        raise FileNotFoundError(
            "resolved_calls.json not found.\n"
            "Run Phase-4 runner first."
        )

    with open(RESOLVED_CALLS_JSON, "r", encoding="utf-8") as f:
        resolved_calls = json.load(f)

    idx = build_index(resolved_calls)

    print("\n=== CallGraphIndex Stats ===")
    print(idx.stats())

    # ---- Example queries ----
    target = "testing_repo.test.Student.display"
    print(f"\n=== Callers of {target} ===")
    for cs in idx.callers_of(target):
        print(f"- {cs.caller_fqn} (line {cs.line})")

    caller = "testing_repo.test.Student.info"
    print(f"\n=== Callees of {caller} ===")
    for cs in idx.callees_of(caller):
        print(f"- {cs.callee_fqn} (line {cs.line})")

    print("\n=== Unresolved Calls (first 10) ===")
    for cs in idx.unresolved_calls()[:10]:
        print(f"- {cs.caller_fqn} -> {cs.callee_name} (line {cs.line})")


if __name__ == "__main__":
    main()

