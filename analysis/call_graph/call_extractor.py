# AST Call detection

import ast
from analysis.utils.bom_handler import read_source_file, parse_source_to_ast

class FunctionCallVisitor(ast.NodeVisitor):
    def __init__(self, file_path):
        self.file_path = file_path
        self.current_function = None
        self.current_class = None   # already existed ✔
        self.calls = []

    # 🔑 ADDED: track class context
    def visit_ClassDef(self, node):
        previous_class = self.current_class
        self.current_class = node.name

        self.generic_visit(node)

        self.current_class = previous_class

    def visit_FunctionDef(self, node):
        previous_function = self.current_function
        self.current_function = node.name

        self.generic_visit(node)

        self.current_function = previous_function

    def visit_Call(self, node):
        if self.current_function is None:
            return

        func_name = self._get_call_name(node.func)

        obj_name = None
        call_class = self.current_class
        call_type = "local"
        target = func_name

        # obj.foo()
        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            obj_name = node.func.value.id

            # 🔑 ADDED: self.method() resolution
            if obj_name == "self" and self.current_class:
                call_type = "method"
                target = f"{self.current_class}.{func_name}"
            else:
                call_type = "attribute"
                target = f"{obj_name}.{func_name}"

        # builtin function
        elif isinstance(node.func, ast.Name):
            if func_name in dir(__builtins__):
                call_type = "builtin"
                target = f"builtins.{func_name}"

        if func_name:
            self.calls.append({
                "caller": self.current_function,
                "class": call_class,
                "object": obj_name,
                "callee": func_name,
                "line": node.lineno,
                "file": self.file_path,
                "call_type": call_type,     # 🔑 ADDED
                "target": target            # 🔑 ADDED
            })

        self.generic_visit(node)

    def _get_call_name(self, node):
        # foo()
        if isinstance(node, ast.Name):
            return node.id

        # obj.foo()
        elif isinstance(node, ast.Attribute):
            return node.attr

        return None


def extract_function_calls(file_path):
    source = read_source_file(file_path)
    tree = parse_source_to_ast(source, file_path=file_path)

    visitor = FunctionCallVisitor(file_path)
    visitor.visit(tree)

    return visitor.calls
