#!/usr/bin/env python3
"""
Universal BOM (Byte Order Mark) Fixer

Removes UTF-8 BOM (U+FEFF) from all Python files in a directory.
This fixes the error: "invalid non-printable character U+FEFF"

Usage:
    python fix_bom.py <path_to_repo>
    
Example:
    python fix_bom.py D:\pythonFiles\testr
    python fix_bom.py D:\pythonFiles\some-repo
"""

import os
import sys
import glob
from pathlib import Path


def fix_bom_in_directory(repo_path):
    """Remove BOM from all Python files in a directory."""
    
    if not os.path.isdir(repo_path):
        print(f"❌ Error: '{repo_path}' is not a valid directory")
        return False
    
    os.chdir(repo_path)
    bom = b'\xef\xbb\xbf'
    fixed_files = []
    errors = []
    
    print(f"🔍 Scanning for BOM files in: {repo_path}\n")
    
    # Find all Python files
    for file_path in glob.glob('**/*.py', recursive=True):
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            
            if content.startswith(bom):
                # Remove BOM and rewrite file
                with open(file_path, 'wb') as f:
                    f.write(content[3:])
                fixed_files.append(file_path)
                print(f"✓ Fixed: {file_path}")
        
        except Exception as e:
            errors.append((file_path, str(e)))
            print(f"⚠ Error processing {file_path}: {e}")
    
    # Print summary
    print("\n" + "="*60)
    if fixed_files:
        print(f"✓ SUCCESS: Fixed {len(fixed_files)} file(s)")
        print("\nFiles fixed:")
        for f in fixed_files:
            print(f"  - {f}")
    else:
        print("✓ No BOM files found - repository is clean!")
    
    if errors:
        print(f"\n⚠ Errors encountered: {len(errors)}")
        for f, err in errors:
            print(f"  - {f}: {err}")
    
    print("="*60)
    return len(fixed_files) > 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    repo_path = sys.argv[1]
    fixed = fix_bom_in_directory(repo_path)
    sys.exit(0 if not fixed else 0)  # Always exit 0
