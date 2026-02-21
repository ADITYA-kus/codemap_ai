# Class Extractor Module
import ast

import ast

def extract_classes(ast_tree, file_path):
    classes = []

    for node in ast.walk(ast_tree):
        if isinstance(node, ast.ClassDef):
            base_classes = []
            methods = []

            # Extract base classes
            for base in node.bases:
                if isinstance(base, ast.Name):
                    base_classes.append(base.id)
                elif isinstance(base, ast.Attribute):
                    base_classes.append(base.attr)

            # Extract methods inside class body
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    methods.append(item.name)

            classes.append({
                "name": node.name,
                "file": file_path,
                "start_line": node.lineno,
                "end_line": node.end_lineno,
                "base_classes": base_classes,
                "methods": methods
            })

    return classes
