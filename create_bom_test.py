#!/usr/bin/env python3
"""Create test repo with BOM files to test CodeMap's BOM handling."""

import os

test_dir = 'd:\\pythonFiles\\bom_test_repo'
os.makedirs(test_dir, exist_ok=True)

# Create a Python file WITH BOM
bom_file = os.path.join(test_dir, 'test_with_bom.py')
with open(bom_file, 'wb') as f:
    f.write(b'\xef\xbb\xbf')  # UTF-8 BOM (U+FEFF)
    f.write(b'def hello_world():\n')
    f.write(b'    """A simple test function."""\n')
    f.write(b'    print("Hello, World!")\n')
    f.write(b'    return True\n')
    f.write(b'\n')
    f.write(b'class TestClass:\n')
    f.write(b'    def method(self):\n')
    f.write(b'        return "test"\n')

# Create a normal file WITHOUT BOM
normal_file = os.path.join(test_dir, 'test_normal.py')
with open(normal_file, 'w', encoding='utf-8') as f:
    f.write('def another_function():\n')
    f.write('    return 42\n')

print(f'✓ Created test repo: {test_dir}')
print(f'  - test_with_bom.py (HAS BOM - U+FEFF)')
print(f'  - test_normal.py (no BOM)')
