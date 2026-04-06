from __future__ import annotations

import ast
import os
from typing import Any, Dict, List, Optional, Set, Tuple

from analysis.utils.bom_handler import read_and_parse_python_file
from analysis.utils.repo_walk import filter_skipped_dirs


_ROUTE_DECORATORS = {
    "get",
    "post",
    "put",
    "delete",
    "patch",
    "options",
    "head",
    "websocket",
    "route",
    "api_route",
}

_CLI_DECORATOR_SUFFIXES = {
    ".command",
    ".group",
    ".callback",
}


def _collect_python_files(repo_dir: str) -> List[str]:
    py_files: List[str] = []
    for root, dirs, files in os.walk(repo_dir):
        dirs[:] = filter_skipped_dirs(dirs)
        for file_name in files:
            if not file_name.endswith(".py"):
                continue
            if file_name.startswith("__") and file_name != "__main__.py":
                continue
            py_files.append(os.path.join(root, file_name))
    return sorted(py_files)


def _file_to_module(file_path: str, repo_root: str, repo_prefix: str) -> str:
    rel = os.path.relpath(os.path.abspath(file_path), os.path.abspath(repo_root)).replace(os.sep, ".")
    if rel.endswith(".py"):
        rel = rel[:-3]
    prefix = str(repo_prefix or os.path.basename(os.path.abspath(repo_root).rstrip("\\/"))).strip()
    return f"{prefix}.{rel}" if prefix else rel


def _dotted_name(node: ast.AST) -> str:
    if isinstance(node, ast.Call):
        return _dotted_name(node.func)
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _dotted_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


def _str_constant(node: Optional[ast.AST]) -> str:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return ""


def _main_guard(node: ast.AST) -> bool:
    if not isinstance(node, ast.If):
        return False
    test = node.test
    if not isinstance(test, ast.Compare) or len(test.ops) != 1 or len(test.comparators) != 1:
        return False
    left = test.left
    right = test.comparators[0]
    if not isinstance(test.ops[0], ast.Eq):
        return False
    return (
        isinstance(left, ast.Name)
        and left.id == "__name__"
        and isinstance(right, ast.Constant)
        and right.value == "__main__"
    )


class _EntryPointVisitor(ast.NodeVisitor):
    def __init__(self, module: str, file_path: str):
        self.module = module
        self.file_path = file_path
        self.class_stack: List[str] = []
        self.entries: List[Dict[str, Any]] = []
        self._seen: Set[Tuple[str, str, int]] = set()

    def _fqn_for(self, name: str) -> str:
        if self.class_stack:
            return f"{self.module}.{'.'.join(self.class_stack)}.{name}"
        return f"{self.module}.{name}"

    def _add_entry(
        self,
        *,
        kind: str,
        title: str,
        reason: str,
        line: int,
        fqn: Optional[str] = None,
    ) -> None:
        key = (str(kind), str(fqn or title), int(line or 1))
        if key in self._seen:
            return
        self._seen.add(key)
        self.entries.append(
            {
                "kind": kind,
                "title": title,
                "reason": reason,
                "fqn": fqn or "",
                "file": self.file_path,
                "line": int(line or 1),
            }
        )

    def _record_function_entrypoints(self, node: ast.AST, name: str, decorators: List[ast.AST]) -> None:
        fqn = self._fqn_for(name)
        for decorator in decorators:
            dotted = _dotted_name(decorator)
            if not dotted:
                continue
            last = dotted.split(".")[-1].lower()
            if last in _ROUTE_DECORATORS:
                path = ""
                if isinstance(decorator, ast.Call) and decorator.args:
                    path = _str_constant(decorator.args[0])
                method_label = "Web route" if last in {"route", "api_route"} else last.upper()
                title = f"{method_label} {path}".strip()
                reason = "This function looks like a web request entry point."
                self._add_entry(
                    kind="api_route",
                    title=title,
                    reason=reason,
                    line=getattr(node, "lineno", 1),
                    fqn=fqn,
                )
            if any(dotted.endswith(suffix) for suffix in _CLI_DECORATOR_SUFFIXES) or dotted.startswith("click.") or dotted.startswith("typer."):
                self._add_entry(
                    kind="cli_command",
                    title=f"CLI command: {name}",
                    reason="This function looks like a command-line entry point.",
                    line=getattr(node, "lineno", 1),
                    fqn=fqn,
                )

        if not self.class_stack and name == "main":
            self._add_entry(
                kind="script_start",
                title="Script start: main()",
                reason="This is a common starting function for running the file directly.",
                line=getattr(node, "lineno", 1),
                fqn=fqn,
            )

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.class_stack.append(node.name)
        self.generic_visit(node)
        self.class_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._record_function_entrypoints(node, node.name, list(node.decorator_list or []))
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._record_function_entrypoints(node, node.name, list(node.decorator_list or []))
        self.generic_visit(node)

    def visit_If(self, node: ast.If) -> None:
        if _main_guard(node):
            module_fqn = f"{self.module}.<module>"
            self._add_entry(
                kind="script_start",
                title="Run this file directly",
                reason="This file has a __main__ block, so it can start execution directly.",
                line=getattr(node, "lineno", 1),
                fqn=module_fqn,
            )
            for child in ast.walk(node):
                if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
                    called_name = child.func.id
                    if called_name:
                        self._add_entry(
                            kind="script_start",
                            title=f"Script start: {called_name}()",
                            reason="This function is called from the file's __main__ block.",
                            line=getattr(child, "lineno", getattr(node, "lineno", 1)),
                            fqn=f"{self.module}.{called_name}",
                        )
        self.generic_visit(node)


def detect_entry_points(repo_dir: str, repo_prefix: str = "") -> List[Dict[str, Any]]:
    repo_root = os.path.abspath(repo_dir)
    prefix = str(repo_prefix or os.path.basename(repo_root.rstrip("\\/"))).strip()
    rows: List[Dict[str, Any]] = []

    for file_path in _collect_python_files(repo_root):
        try:
            tree = read_and_parse_python_file(file_path)
        except Exception:
            continue
        module = _file_to_module(file_path, repo_root, prefix)
        visitor = _EntryPointVisitor(module=module, file_path=file_path)
        visitor.visit(tree)
        rows.extend(visitor.entries)

    order = {"api_route": 0, "cli_command": 1, "script_start": 2}
    rows.sort(key=lambda item: (order.get(str(item.get("kind", "")), 99), str(item.get("file", "")), int(item.get("line", 1))))
    return rows[:50]
