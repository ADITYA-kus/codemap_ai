# Function Extractor Module
import ast

def extract_functions(ast_tree, file_path):
    functions = []

    for node in ast.walk(ast_tree):
        if isinstance(node, ast.FunctionDef):
            functions.append({
                "fun_name": node.name,
                "file_name": file_path,
                "start_line": node.lineno,
                "end_line": node.end_lineno
            })

    return functions
