# Orchestrates per-symbol explain
# analysis/explain/explain_runner.py

from __future__ import annotations

from typing import Optional, Dict, Any

import json
import os

from analysis.indexing.symbol_index import SymbolIndex, SymbolInfo
from analysis.graph.callgraph_index import CallGraphIndex, CallSite
from analysis.explain.docstring_extractor import extract_docstrings
from analysis.explain.signature_extractor import extract_signatures
from analysis.explain.return_analyzer import analyze_returns
from analysis.explain.summary_generator import generate_symbol_summary


def collect_python_files(root_dir: str):
    py_files = []
    for root, _, files in os.walk(root_dir):
        for file in files:
            if file.endswith(".py") and not file.startswith("__"):
                py_files.append(os.path.join(root, file))
    return py_files


def parse_ast(file_path: str):
    """Parse a Python file with automatic encoding and BOM handling."""
    from analysis.utils.bom_handler import read_and_parse_python_file
    return read_and_parse_python_file(file_path)


def file_to_module(file_path: str, repo_root: str) -> str:
    repo_root = os.path.abspath(repo_root)
    file_path = os.path.abspath(file_path)

    rel = os.path.relpath(file_path, repo_root)
    rel = rel.replace(os.sep, ".")
    if rel.endswith(".py"):
        rel = rel[:-3]

    # Prefix with folder name so symbols don’t collide across repos
    repo_name = os.path.basename(repo_root.rstrip("\\/"))
    return f"{repo_name}.{rel}"



def build_callgraph_from_resolved_calls_json(path: str) -> CallGraphIndex:
    with open(path, "r", encoding="utf-8") as f:
        resolved_calls = json.load(f)

    idx = CallGraphIndex()
    for c in resolved_calls:
        idx.add_call(
            CallSite(
                caller_fqn=c["caller_fqn"],
                callee_fqn=c.get("callee_fqn"),
                callee_name=c.get("callee", "<unknown>"),
                file=c.get("file", ""),
                line=int(c.get("line", -1)),
            )
        )
    return idx


def symbol_fqn(sym: SymbolInfo) -> str:
    return f"{sym.module}.{sym.qualified_name}"


def merge_maps(dst: dict, src: dict):
    """
    Merge extractor outputs across files into single dicts.
    """
    dst["module"] = dst.get("module")
    for k in ("classes", "functions", "methods"):
        dst.setdefault(k, {})
        dst[k].update(src.get(k, {}))


def run(repo_dir: Optional[str] = None, output_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    Callable explain pipeline (Phase-5/6), suitable for CLI/VS Code.

    Args:
        repo_dir: directory to analyze (default: analysis/testing_repo)
        output_dir: directory to write outputs (default: analysis/output)

    Returns:
        {
          "explain_path": ".../explain.json",
          "symbols": <int>
        }
    """
    analysis_root = os.path.dirname(os.path.dirname(__file__))  # /analysis

    if repo_dir is None:
        repo_dir = os.path.join(analysis_root, "testing_repo")

    if output_dir is None:
        output_dir = os.path.join(analysis_root, "output")

    os.makedirs(output_dir, exist_ok=True)

    resolved_calls_json = os.path.join(output_dir, "resolved_calls.json")
    if not os.path.exists(resolved_calls_json):
        raise FileNotFoundError(
            f"Missing: {resolved_calls_json}\nRun Phase-4 first."
        )

    # 1) Load callgraph
    callgraph = build_callgraph_from_resolved_calls_json(resolved_calls_json)

    # 2) Collect repo python files
    python_files = collect_python_files(repo_dir)

    # 3) Build symbol index + extractors across repo
    symbol_index = SymbolIndex()

    repo_docstrings = {"module": None, "classes": {}, "functions": {}, "methods": {}}
    repo_signatures = {"functions": {}, "methods": {}}
    repo_returns = {"functions": {}, "methods": {}}

    for file_path in python_files:
        tree = parse_ast(file_path)
        module_path = file_to_module(file_path, repo_dir)


        # index symbols
        symbol_index.index_file(tree, module_path, file_path)

        # extract per-file and merge
        merge_maps(repo_docstrings, extract_docstrings(tree))

        sigs = extract_signatures(tree)
        repo_signatures["functions"].update(sigs.get("functions", {}))
        repo_signatures["methods"].update(sigs.get("methods", {}))

        rets = analyze_returns(tree)
        repo_returns["functions"].update(rets.get("functions", {}))
        repo_returns["methods"].update(rets.get("methods", {}))

    # 4) Generate summaries for all symbols
    explain: Dict[str, dict] = {}

    for sym in symbol_index.all_symbols():
        fqn = symbol_fqn(sym)
        explain[fqn] = generate_symbol_summary(
            symbol_fqn=fqn,
            symbol_info=sym,
            docstrings=repo_docstrings,
            signatures=repo_signatures,
            returns=repo_returns,
            callgraph=callgraph,
        )

    # 5) Save explain.json
    explain_path = os.path.join(output_dir, "explain.json")
    with open(explain_path, "w", encoding="utf-8") as f:
        json.dump(explain, f, indent=2)

    return {
        "explain_path": explain_path,
        "symbols": len(explain),
    }


def main():
    print("\n=== Phase-5 Explain Runner ===\n")
    result = run()
    print(f"Saved: {result['explain_path']}")
    print(f"Symbols explained: {result['symbols']}")
    print("\n=== Phase-5 Step-6 Complete ===\n")


if __name__ == "__main__":
    main()
