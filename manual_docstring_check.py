"""
Manual verification for Phase-5 Step-2.1 (Docstring Extractor)

This test:
- parses a target Python file
- extracts module / class / function / method docstrings
- prints them for visual verification

Safe to delete anytime.
"""

import ast
import os

from analysis.explain.docstring_extractor import extract_docstrings

# Adjust this path if your test file is elsewhere
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
TARGET_FILE = os.path.join(PROJECT_ROOT, "code_assist_phase2","analysis","testing_repo","test.py")

def main():
    if not os.path.exists(TARGET_FILE):
        raise FileNotFoundError(f"Target file not found: {TARGET_FILE}")

    with open(TARGET_FILE, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())

    docs = extract_docstrings(tree)

    print("\n=== Module Docstring ===")
    print(docs["module"])

    print("\n=== Class Docstrings ===")
    for cls, doc in docs["classes"].items():
        print(f"\n[{cls}]")
        print(doc)

    print("\n=== Function Docstrings ===")
    for fn, doc in docs["functions"].items():
        print(f"\n[{fn}]")
        print(doc)

    print("\n=== Method Docstrings ===")
    for m, doc in docs["methods"].items():
        print(f"\n[{m}]")
        print(doc)


if __name__ == "__main__":
    main()
