"""
Manual verification for Phase-5 Step-3.1 (Signature Extractor)

- Parses a target Python file
- Prints extracted function + method signatures
"""

import ast
import os
import pprint

from analysis.explain.signature_extractor import extract_signatures

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
TARGET_FILE = os.path.join(PROJECT_ROOT, "code_assist_phase2","analysis","testing_repo","test.py")


def main():
    if not os.path.exists(TARGET_FILE):
        raise FileNotFoundError(f"Target file not found: {TARGET_FILE}")

    with open(TARGET_FILE, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())

    sigs = extract_signatures(tree)

    print("\n=== Function Signatures ===")
    pprint.pprint(sigs["functions"], width=120)

    print("\n=== Method Signatures ===")
    pprint.pprint(sigs["methods"], width=120)


if __name__ == "__main__":
    main()
