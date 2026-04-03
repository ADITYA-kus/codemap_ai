# Heuristic summary (no LLM yet)
# analysis/explain/summary_generator.py
# Phase-5 Step-5.1: Heuristic summary generator (no LLM)

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, Optional, List

from analysis.indexing.symbol_index import SymbolInfo
from analysis.graph.callgraph_index import CallGraphIndex


def _first_line(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    stripped = text.strip()
    if not stripped:
        return None
    line = stripped.splitlines()[0].strip()
    return line or None


def _humanize_name(name: str) -> str:
    # snake_case -> words
    return name.replace("_", " ").strip()


def _format_args(sig: Optional[dict]) -> str:
    if not sig:
        return "()"
    args = sig.get("args", [])
    vararg = sig.get("vararg")
    kwonly = sig.get("kwonlyargs", [])
    kwarg = sig.get("kwarg")

    parts: List[str] = []
    parts.extend(args)

    if vararg:
        parts.append(f"*{vararg}")

    if kwonly:
        # show marker for kw-only if not already implied by *args
        if not vararg:
            parts.append("*")
        parts.extend(kwonly)

    if kwarg:
        parts.append(f"**{kwarg}")

    return "(" + ", ".join(parts) + ")"


def _return_phrase(ret_info: Optional[dict]) -> str:
    if not ret_info:
        return "Returns: unknown."

    kinds = ret_info.get("return_kinds", [])
    if kinds == ["none"]:
        return "Returns: None."
    if "call" in kinds:
        return "Returns: result of a call."
    if "expression" in kinds:
        return "Returns: computed value."
    if "name" in kinds:
        return "Returns: a variable value."
    if "constant" in kinds:
        return "Returns: a constant."
    if "attribute" in kinds:
        return "Returns: an attribute value."
    return "Returns: mixed/complex."


def _tags_from_callees(callee_fqns: List[str]) -> List[str]:
    tags: List[str] = []
    if any(c == "builtins.print" for c in callee_fqns):
        tags.append("io:print")
    if any(c == "builtins.open" for c in callee_fqns):
        tags.append("io:file")
    if any("read" in c.lower() or "load" in c.lower() for c in callee_fqns):
        tags.append("io:read")
    if any("write" in c.lower() or "save" in c.lower() for c in callee_fqns):
        tags.append("io:write")
    return tags


def _analyze_method_behavior(symbol_info: SymbolInfo, callee_fqns: List[str]) -> str:
    """Analyze what a method does based on its callees and name patterns."""
    name = symbol_info.name.lower()
    
    # Check for initialization patterns
    if name in ("__init__", "init", "initialize", "setup"):
        return "initializes the object"
    
    # Check for display/output patterns
    if any(word in name for word in ["display", "show", "print", "render"]):
        if any("print" in c for c in callee_fqns):
            return "displays information to console"
        return "displays information"
    
    # Check for data setting patterns
    if any(word in name for word in ["set", "update", "assign", "configure"]):
        return "sets or updates internal state"
    
    # Check for data retrieval patterns
    if any(word in name for word in ["get", "fetch", "retrieve", "load"]):
        return "retrieves or loads data"
    
    # Check for validation patterns
    if any(word in name for word in ["validate", "check", "verify", "test"]):
        return "validates or checks conditions"
    
    # Check for computation patterns
    if any(word in name for word in ["calculate", "compute", "process", "transform"]):
        return "performs calculations or transformations"
    
    # Check based on callees
    if callee_fqns:
        if any("display" in c.lower() or "show" in c.lower() for c in callee_fqns):
            return "orchestrates display operations"
        if any("save" in c.lower() or "write" in c.lower() for c in callee_fqns):
            return "saves or persists data"
    
    return None


def generate_symbol_summary(
    symbol_fqn: str,
    symbol_info: SymbolInfo,
    docstrings: dict,
    signatures: dict,
    returns: dict,
    callgraph: CallGraphIndex
) -> Dict[str, Any]:
    """
    Generate a heuristic summary for one symbol.
    """

    # -------- Docstring lookup --------
    doc: Optional[str] = None
    if symbol_info.kind.value in ("method",):
        # methods dict uses "Class.method"
        key = symbol_info.qualified_name
        doc = docstrings.get("methods", {}).get(key)
    elif symbol_info.kind.value in ("function",):
        key = symbol_info.name
        doc = docstrings.get("functions", {}).get(key)
    elif symbol_info.kind.value in ("class",):
        key = symbol_info.name
        doc = docstrings.get("classes", {}).get(key)

    doc_first = _first_line(doc)

    # -------- Signature lookup --------
    sig: Optional[dict] = None
    if symbol_info.kind.value == "method":
        sig = signatures.get("methods", {}).get(symbol_info.qualified_name)
    elif symbol_info.kind.value == "function":
        sig = signatures.get("functions", {}).get(symbol_info.name)

    args_str = _format_args(sig)

    # -------- Returns lookup --------
    ret_info: Optional[dict] = None
    if symbol_info.kind.value == "method":
        ret_info = returns.get("methods", {}).get(symbol_info.qualified_name)
    elif symbol_info.kind.value == "function":
        ret_info = returns.get("functions", {}).get(symbol_info.name)

    # -------- Callgraph lookup --------
    callees_sites = callgraph.callees_of(symbol_fqn)
    callers_sites = callgraph.callers_of(symbol_fqn)

    callee_fqns = [cs.callee_fqn for cs in callees_sites if cs.callee_fqn]
    caller_fqns = [cs.caller_fqn for cs in callers_sites]

    callee_counts = Counter(callee_fqns)

    # -------- One-liner --------
    if doc_first:
        one_liner = doc_first
    else:
        # Try to infer behavior from method analysis
        behavior = _analyze_method_behavior(symbol_info, callee_fqns)
        
        if behavior:
            one_liner = f"{symbol_info.name}{args_str} {behavior}."
        else:
            # Heuristic verb phrase from name
            name_phrase = _humanize_name(symbol_info.name)
            if symbol_info.name.startswith("get_"):
                verb = "gets"
                rest = _humanize_name(symbol_info.name[4:])
                one_liner = f"{symbol_info.name}{args_str} {verb} {rest}."
            elif symbol_info.name.startswith("set_"):
                verb = "sets"
                rest = _humanize_name(symbol_info.name[4:])
                one_liner = f"{symbol_info.name}{args_str} {verb} {rest}."
            elif symbol_info.name.startswith("load_"):
                verb = "loads"
                rest = _humanize_name(symbol_info.name[5:])
                one_liner = f"{symbol_info.name}{args_str} {verb} {rest}."
            elif symbol_info.name.startswith("save_"):
                verb = "saves"
                rest = _humanize_name(symbol_info.name[5:])
                one_liner = f"{symbol_info.name}{args_str} {verb} {rest}."
            elif symbol_info.name.startswith("build_"):
                verb = "builds"
                rest = _humanize_name(symbol_info.name[6:])
                one_liner = f"{symbol_info.name}{args_str} {verb} {rest}."
            else:
                one_liner = f"{symbol_info.name}{args_str} does work related to '{name_phrase}'."

    # -------- Details --------
    details: List[str] = []
    
    # Location info
    if symbol_info.file_path and symbol_info.start_line > 0:
        details.append(
            f"Defined in {symbol_info.file_path}:{symbol_info.start_line}-{symbol_info.end_line}"
        )
    
    # Signature details
    if sig:
        sig_parts = []
        if sig.get("args"):
            sig_parts.append(f"Parameters: {', '.join(sig['args'])}")
        if sig.get("vararg"):
            sig_parts.append(f"*args: {sig['vararg']}")
        if sig.get("kwonlyargs"):
            sig_parts.append(f"Keyword-only: {', '.join(sig['kwonlyargs'])}")
        if sig.get("kwarg"):
            sig_parts.append(f"**kwargs: {sig['kwarg']}")
        if sig_parts:
            details.append("Signature: " + "; ".join(sig_parts))
    
    # Caller info
    if caller_fqns:
        unique_callers = sorted(set(caller_fqns))
        if len(unique_callers) <= 3:
            details.append("Called by: " + ", ".join(unique_callers))
        else:
            details.append(f"Called by: {', '.join(unique_callers[:3])} and {len(unique_callers) - 3} more")
    else:
        details.append("Called by: (no callers found)")

    # Callee info with better formatting
    if callee_counts:
        calls_list = []
        for name, cnt in callee_counts.most_common(8):
            short_name = name.split(".")[-1] if "." in name else name
            if cnt > 1:
                calls_list.append(f"{short_name}() x{cnt}")
            else:
                calls_list.append(f"{short_name}()")
        details.append("Calls: " + ", ".join(calls_list))
    else:
        details.append("Calls: (no callees found)")

    # Return info
    ret_phrase = _return_phrase(ret_info)
    if ret_info and ret_info.get("examples"):
        examples = ret_info["examples"][:2]
        ret_phrase += f" Examples: {', '.join(examples)}"
    details.append(ret_phrase)

    tags = _tags_from_callees(callee_fqns)


    location = {
        "file": symbol_info.file_path,
        "start_line": symbol_info.start_line,
        "end_line": symbol_info.end_line,
    }



    return {
        "fqn": symbol_fqn,
        "one_liner": one_liner,
        "details": details,
        "tags": tags,
        "location":location,
    }
