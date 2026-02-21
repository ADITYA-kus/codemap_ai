# Args, defaults, *args/**kwargs

# analysis/explain/signature_extractor.py
# Phase-5 Step-3.1: Extract function/method signatures from AST

import ast
from typing import Any, Dict, Optional


def _safe_unparse(node: Optional[ast.AST]) -> Optional[str]:
    if node is None:
        return None
    try:
        return ast.unparse(node)
    except Exception:
        return None


def _extract_signature_dict(fn: ast.FunctionDef) -> Dict[str, Any]:
    """
    Extract a normalized signature dict from a FunctionDef node.
    """
    args = fn.args

    # Positional-or-keyword parameters
    pos_args = [a.arg for a in args.args]

    # Keyword-only parameters
    kwonly_args = [a.arg for a in args.kwonlyargs]

    # *args / **kwargs
    vararg = args.vararg.arg if args.vararg else None
    kwarg = args.kwarg.arg if args.kwarg else None

    # Defaults apply to the LAST N positional-or-keyword params
    defaults_map: Dict[str, Optional[str]] = {}
    if args.defaults:
        default_values = [_safe_unparse(d) for d in args.defaults]
        default_param_names = pos_args[-len(default_values):]
        defaults_map = dict(zip(default_param_names, default_values))

    # Keyword-only defaults map (kw_defaults aligns with kwonlyargs)
    kwonly_defaults_map: Dict[str, Optional[str]] = {}
    if args.kwonlyargs:
        for name_node, def_node in zip(args.kwonlyargs, args.kw_defaults):
            kwonly_defaults_map[name_node.arg] = _safe_unparse(def_node)

    # Type annotations for params + return
    annotations: Dict[str, Optional[str]] = {}
    for a in args.args:
        if a.annotation is not None:
            annotations[a.arg] = _safe_unparse(a.annotation)
    for a in args.kwonlyargs:
        if a.annotation is not None:
            annotations[a.arg] = _safe_unparse(a.annotation)
    if args.vararg and args.vararg.annotation is not None:
        annotations[f"*{args.vararg.arg}"] = _safe_unparse(args.vararg.annotation)
    if args.kwarg and args.kwarg.annotation is not None:
        annotations[f"**{args.kwarg.arg}"] = _safe_unparse(args.kwarg.annotation)

    if fn.returns is not None:
        annotations["return"] = _safe_unparse(fn.returns)

    return {
        "args": pos_args,
        "defaults": defaults_map,
        "kwonlyargs": kwonly_args,
        "kwonly_defaults": kwonly_defaults_map,
        "vararg": vararg,
        "kwarg": kwarg,
        "annotations": annotations,
    }


def extract_signatures(ast_tree: ast.AST) -> Dict[str, Dict[str, Any]]:
    """
    Extract signatures for:
      - top-level functions
      - class methods

    Returns:
      {
        "functions": { "func": signature_dict },
        "methods": { "Class.method": signature_dict }
      }
    """
    result: Dict[str, Dict[str, Any]] = {
        "functions": {},
        "methods": {},
    }

    for node in ast_tree.body:
        # Top-level functions
        if isinstance(node, ast.FunctionDef):
            result["functions"][node.name] = _extract_signature_dict(node)

        # Classes and methods
        elif isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    key = f"{node.name}.{item.name}"
                    result["methods"][key] = _extract_signature_dict(item)

    return result
