# AST Parser Module
import ast
def parse_python_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        source = f.read()

    return ast.parse(source)

