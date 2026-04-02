# Import Extractor Module
# analysis/import_extractor.py

import ast
from analysis.utils.bom_handler import read_source_file, parse_source_to_ast


def extract_imports(file_path):
    """Extract imports from a Python file with automatic encoding and BOM handling."""
    source = read_source_file(file_path)
    tree = parse_source_to_ast(source, file_path=file_path)
    
    imports = []

    for node in ast.walk(tree):

        # import module
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append({
                    "type": "import",
                    "module": alias.name,
                    "name": None,
                    "alias": alias.asname,
                    "line": node.lineno,
                    "file": file_path
                })

        # from module import name
        elif isinstance(node, ast.ImportFrom):
            module = node.module
            level = node.level  # 0 = absolute, >0 = relative

            for alias in node.names:
                imports.append({
                    "type": "from_import",
                    "module": module,
                    "name": alias.name,
                    "alias": alias.asname,
                    "level": level,
                    "line": node.lineno,
                    "file": file_path
                })

    return imports
