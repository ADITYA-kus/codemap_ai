"""
Manual verification for Phase-5 Step-4.1 (Return Analyzer)

- Parses a target Python file
- Prints analyzed return info for functions and methods
"""

import ast
import os
import pprint

from analysis.explain.return_analyzer import analyze_returns

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
TARGET_FILE = os.path.join(PROJECT_ROOT, "code_assist_phase2","analysis","testing_repo","test.py")


def main():
    if not os.path.exists(TARGET_FILE):
        raise FileNotFoundError(f"Target file not found: {TARGET_FILE}")

    with open(TARGET_FILE, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())

    result = analyze_returns(tree)

    print("\n=== Function Returns ===")
    pprint.pprint(result["functions"], width=120)

    print("\n=== Method Returns ===")
    pprint.pprint(result["methods"], width=120)


if __name__ == "__main__":
    main()
