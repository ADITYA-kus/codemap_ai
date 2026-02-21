"""
Manual verification for Phase-5 Step-5.1 (Summary Generator)

Pipeline:
- Run Phase-4 first to generate resolved_calls.json
- This script loads resolved_calls.json, builds CallGraphIndex
- Parses a target python file and extracts docstrings/signatures/returns
- Builds SymbolIndex and finds SymbolInfo for a given FQN
- Generates and prints summary
"""

import ast
import json
import os
import pprint

from analysis.indexing.symbol_index import SymbolIndex
from analysis.graph.callgraph_index import CallGraphIndex, CallSite
from analysis.explain.docstring_extractor import extract_docstrings
from analysis.explain.signature_extractor import extract_signatures
from analysis.explain.return_analyzer import analyze_returns
from analysis.explain.summary_generator import generate_symbol_summary

WORKSPACE_ROOT = os.path.dirname(os.path.abspath(__file__))   # repo root
ANALYSIS_ROOT = os.path.join(WORKSPACE_ROOT, "analysis")      # analysis folder

# Define target file and resolved calls JSON
TARGET_FILE = os.path.join(ANALYSIS_ROOT, "testing_repo", "test.py")
RESOLVED_CALLS_JSON = os.path.join(ANALYSIS_ROOT, "output", "resolved_calls.json")

TARGET_MODULE = "testing_repo.test"  # Changed to match resolved_calls.json format

# Choose one symbol to summarize:
# Note: Change this to match symbols in your resolved_calls.json
# Available: Student.info, Student.display, Student.__init__, introduction
TARGET_SYMBOL_FQN = f"{TARGET_MODULE}.Student.info"  # Using Student (not Student1)


def file_to_module(file_path: str, project_root: str) -> str:
    """Convert file path to module notation."""
    rel = os.path.relpath(file_path, project_root)
    rel = rel.replace(os.sep, ".")
    if rel.endswith(".py"):
        rel = rel[:-3]
    return rel


def build_callgraph_from_json(path: str) -> CallGraphIndex:
    """Build CallGraphIndex from resolved_calls.json."""
    with open(path, "r", encoding="utf-8") as f:
        resolved_calls = json.load(f)

    idx = CallGraphIndex()
    for c in resolved_calls:
        cs = CallSite(
            caller_fqn=c["caller_fqn"],
            callee_fqn=c.get("callee_fqn"),
            callee_name=c.get("callee", "<unknown>"),
            file=c.get("file", ""),
            line=int(c.get("line", -1)),
        )
        idx.add_call(cs)

    return idx


def parse_ast(file_path: str) -> ast.AST:
    """Parse Python file into AST."""
    with open(file_path, "r", encoding="utf-8") as f:
        return ast.parse(f.read())


def find_symbol_info(symbol_index: SymbolIndex, symbol_fqn: str):
    """
    Convert full FQN -> (module, qualified_name) lookup.
    Example:
      analysis.testing_repo.test.Student1.info1
        module = analysis.testing_repo.test
        qualified_name = Student1.info1
    """
    parts = symbol_fqn.split(".")
    
    # Try method lookup first (Class.method)
    if len(parts) >= 2:
        module = ".".join(parts[:-2])
        qualified_name = ".".join(parts[-2:])
        sym = symbol_index.get(module, qualified_name)
        if sym:
            return sym

    # Fallback: function (module.func)
    module = ".".join(parts[:-1])
    qualified_name = parts[-1]
    return symbol_index.get(module, qualified_name)


def main():
    print(f"Target File: {TARGET_FILE}")
    print(f"Resolved Calls JSON: {RESOLVED_CALLS_JSON}")
    print(f"Target Symbol: {TARGET_SYMBOL_FQN}\n")
    
    if not os.path.exists(RESOLVED_CALLS_JSON):
        raise FileNotFoundError(f"resolved_calls.json not found at: {RESOLVED_CALLS_JSON}\nRun Phase-4 runner first.")

    if not os.path.exists(TARGET_FILE):
        raise FileNotFoundError(f"Target file not found: {TARGET_FILE}")

    # 1) Callgraph
    print("Loading call graph...")
    callgraph = build_callgraph_from_json(RESOLVED_CALLS_JSON)

    # 2) AST extraction
    print("Parsing AST and extracting metadata...")
    tree = parse_ast(TARGET_FILE)
    docstrings = extract_docstrings(tree)
    signatures = extract_signatures(tree)
    returns = analyze_returns(tree)

    # 3) SymbolIndex build (only for this file)
    print("Building symbol index...")
    symbol_index = SymbolIndex()
    # Use "testing_repo.test" to match resolved_calls.json format
    module_path = "testing_repo.test"
    symbol_index.index_file(tree, module_path, TARGET_FILE)

    # 4) Find SymbolInfo
    print(f"Looking up symbol: {TARGET_SYMBOL_FQN}")
    sym = find_symbol_info(symbol_index, TARGET_SYMBOL_FQN)
    if not sym:
        raise ValueError(f"Symbol not found in SymbolIndex: {TARGET_SYMBOL_FQN}")

    # 5) Generate summary
    print("Generating summary...\n")
    summary = generate_symbol_summary(
        symbol_fqn=TARGET_SYMBOL_FQN,
        symbol_info=sym,
        docstrings=docstrings,
        signatures=signatures,
        returns=returns,
        callgraph=callgraph,
    )

    print("\n" + "="*80)
    print("SYMBOL SUMMARY")
    print("="*80)
    print(f"\nFQN: {summary['fqn']}")
    print(f"\n{summary['one_liner']}")
    print("\nDetails:")
    for i, detail in enumerate(summary['details'], 1):
        print(f"  {i}. {detail}")
    
    if summary['tags']:
        print(f"\nTags: {', '.join(summary['tags'])}")
    else:
        print("\nTags: (none)")
    
    print("\n" + "="*80)
    print("\nRaw JSON output:")
    print("="*80)
    pprint.pprint(summary, width=120)


if __name__ == "__main__":
    main()
