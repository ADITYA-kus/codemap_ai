# Orchestrates Phase-4 pipeline
from __future__ import annotations

from typing import Optional, Dict, Any, List

import os
import json
from analysis.indexing.symbol_index import SymbolIndex
from analysis.indexing.import_resolver import ImportResolver
from analysis.call_graph.cross_file_resolver import CrossFileResolver
from analysis.call_graph.call_extractor import extract_function_calls
from analysis.core.import_extractor import extract_imports
from analysis.graph.callgraph_index import build_caller_fqn


PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))


def collect_python_files(root_dir: str) -> List[str]:
    ignore_dirs = {".git", "__pycache__", ".codemap_cache", "node_modules", ".venv", "venv"}
    py_files: List[str] = []
    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        for file in files:
            if file.endswith(".py") and not file.startswith("__"):
                py_files.append(os.path.join(root, file))
    return py_files


def parse_ast(file_path: str):
    """Parse a Python file, automatically handling encoding and UTF-8 BOM."""
    from analysis.utils.bom_handler import read_and_parse_python_file
    return read_and_parse_python_file(file_path)


def file_to_module(file_path: str, repo_root: str) -> str:
    repo_root = os.path.abspath(repo_root)
    file_path = os.path.abspath(file_path)

    rel = os.path.relpath(file_path, repo_root).replace(os.sep, ".")
    if rel.endswith(".py"):
        rel = rel[:-3]

    repo_name = os.path.basename(repo_root.rstrip("\\/"))
    return f"{repo_name}.{rel}"


def _symbol_snapshot(symbol_index: SymbolIndex) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for sym in symbol_index.all_symbols():
        rows.append(
            {
                "name": str(sym.name),
                "qualified_name": str(sym.qualified_name),
                "kind": str(getattr(sym.kind, "value", str(sym.kind))),
                "module": str(sym.module),
                "file_path": str(sym.file_path),
                "start_line": int(sym.start_line),
                "end_line": int(sym.end_line),
                "class_name": sym.class_name,
                "metadata": dict(sym.metadata or {}),
            }
        )
    return rows


def run(repo_dir: Optional[str] = None, output_dir: Optional[str] = None, force_rebuild: bool = False) -> Dict[str, Any]:
    analysis_root = os.path.dirname(os.path.dirname(__file__))

    if repo_dir is None:
        repo_dir = os.path.join(analysis_root, "testing_repo")

    if output_dir is None:
        output_dir = os.path.join(analysis_root, "output")

    os.makedirs(output_dir, exist_ok=True)

    python_files = collect_python_files(repo_dir)
    symbol_index = SymbolIndex()
    file_module_map: Dict[str, str] = {}

    for file_path in python_files:
        module_path = file_to_module(file_path, repo_dir)
        file_module_map[file_path] = module_path
        tree = parse_ast(file_path)
        symbol_index.index_file(tree, module_path, file_path)

    import_resolver = ImportResolver(symbol_index)
    for file_path in python_files:
        module_path = file_module_map[file_path]
        imports = extract_imports(file_path)
        import_resolver.index_module_imports(module_path, imports)

    all_calls = []
    for file_path in python_files:
        all_calls.extend(extract_function_calls(file_path))

    cross_resolver = CrossFileResolver(symbol_index, import_resolver)
    resolved_calls = []
    for call in all_calls:
        call_file = call.get("file")
        current_module = file_module_map.get(call_file)
        symbol = cross_resolver.resolve_call(call, current_module)
        caller_fqn = build_caller_fqn(call, current_module)
        callee_fqn = f"{symbol.module}.{symbol.qualified_name}" if symbol else None
        resolved_calls.append({
            **call,
            "caller_fqn": caller_fqn,
            "callee_fqn": callee_fqn,
            "resolved_target": callee_fqn,
        })

    resolved_calls_path = os.path.join(output_dir, "resolved_calls.json")
    with open(resolved_calls_path, "w", encoding="utf-8") as f:
        json.dump(resolved_calls, f, indent=2)

    return {
        "resolved_calls_path": resolved_calls_path,
        "total_calls": len(resolved_calls),
        "incremental": False,
        "reindexed_files": len(python_files),
        "impacted_files": len(python_files),
        "symbol_snapshot": _symbol_snapshot(symbol_index),
        "imports_snapshot": {},
        "file_module_map": file_module_map,
        "force_rebuild": bool(force_rebuild),
    }


def main():
    result = run()
    print(f"Saved: {result['resolved_calls_path']}")
    print(f"Total calls: {result['total_calls']}")


if __name__ == "__main__":
    main()
