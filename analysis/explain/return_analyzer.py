# Detect return patterns
# analysis/explain/return_analyzer.py
# Phase-5 Step-4.1: Analyze return statements from AST (static)

import ast
from typing import Any, Dict, Optional, Set, List


def _safe_unparse(node: Optional[ast.AST]) -> Optional[str]:
    if node is None:
        return None
    try:
        return ast.unparse(node)
    except Exception:
        return None


def _classify_return_value(value: Optional[ast.AST]) -> str:
    """
    Classify a return expression node into a simple category.
    """
    if value is None:
        return "none"

    # return None
    if isinstance(value, ast.Constant) and value.value is None:
        return "none"

    # return 1 / "x" / True
    if isinstance(value, ast.Constant):
        return "constant"

    # return x
    if isinstance(value, ast.Name):
        return "name"

    # return obj.attr
    if isinstance(value, ast.Attribute):
        return "attribute"

    # return foo(...) or obj.foo(...)
    if isinstance(value, ast.Call):
        return "call"

    # Anything else: a+b, f-strings, comprehensions, etc.
    return "expression"


def _analyze_function_returns(fn: ast.FunctionDef) -> Dict[str, Any]:
    return_nodes: List[ast.Return] = [
        n for n in ast.walk(fn) if isinstance(n, ast.Return)
    ]

    kinds: Set[str] = set()
    examples: List[str] = []

    for r in return_nodes:
        kind = _classify_return_value(r.value)
        kinds.add(kind)

        if len(examples) < 3:
            if r.value is None:
                examples.append("None")
            else:
                ex = _safe_unparse(r.value)
                examples.append(ex if ex is not None else "<unparse_failed>")

    # If there are no return statements, Python returns None implicitly
    if not return_nodes:
        return {
            "has_return": False,
            "returns_count": 0,
            "return_kinds": ["none"],
            "examples": [],
        }

    return {
        "has_return": True,
        "returns_count": len(return_nodes),
        "return_kinds": sorted(kinds),
        "examples": examples,
    }


def analyze_returns(ast_tree: ast.AST) -> Dict[str, Dict[str, Any]]:
    """
    Analyze returns for:
      - top-level functions
      - class methods

    Returns:
      {
        "functions": { "func": return_info },
        "methods": { "Class.method": return_info }
      }
    """
    result: Dict[str, Dict[str, Any]] = {
        "functions": {},
        "methods": {},
    }

    for node in ast_tree.body:
        # Top-level functions
        if isinstance(node, ast.FunctionDef):
            result["functions"][node.name] = _analyze_function_returns(node)

        # Classes and methods
        elif isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    key = f"{node.name}.{item.name}"
                    result["methods"][key] = _analyze_function_returns(item)

    return result
