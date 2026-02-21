# Get docstrings from AST
# analysis/explain/docstring_extractor.py
# Phase-5 Step-2.1: Extract module/class/function/method docstrings from AST

import ast
from typing import Dict, Optional


def extract_docstrings(ast_tree: ast.AST) -> Dict[str, object]:
    """
    Extract docstrings from a parsed AST tree.

    Returns:
        {
          "module": Optional[str],
          "classes": Dict[str, Optional[str]],
          "functions": Dict[str, Optional[str]],
          "methods": Dict[str, Optional[str]]   # key = "ClassName.method"
        }
    """
    result = {
        "module": ast.get_docstring(ast_tree),
        "classes": {},
        "functions": {},
        "methods": {},
    }

    # Only immediate children are needed for docstrings;
    # ast.walk would include nested defs which we don't want for Phase-5.
    for node in ast_tree.body:
        # Top-level functions
        if isinstance(node, ast.FunctionDef):
            result["functions"][node.name] = ast.get_docstring(node)

        # Classes
        elif isinstance(node, ast.ClassDef):
            result["classes"][node.name] = ast.get_docstring(node)

            # Methods inside class
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    key = f"{node.name}.{item.name}"
                    result["methods"][key] = ast.get_docstring(item)

    return result
