from analysis.ast_parser import parse_python_file
from analysis.function_extractor import extract_functions
from analysis.class_extractor import extract_classes
from analysis.import_extractor import extract_imports
import ast 
tree = parse_python_file(r"analysis\test.py")

functions = extract_functions(tree, r"analysis\test.py")
classes = extract_classes(tree, r"analysis\test.py")
imports = extract_imports(r"analysis/test.py")


# day 2:

import ast
from analysis.function_extractor import extract_functions
from analysis.call_graph.call_extractor import extract_function_calls
from analysis.call_graph.call_resolver import resolve_calls
from analysis.import_extractor import extract_imports

file_path = "analysis/test.py"

# build AST once
with open(file_path, "r", encoding="utf-8") as f:
    ast_tree = ast.parse(f.read())

# Phase-3 Step-1
calls = extract_function_calls(file_path)

# Phase-2 reuse (FIXED)
functions = extract_functions(ast_tree, file_path)
local_function_names = [f["fun_name"] for f in functions]

imports = extract_imports(file_path)

# Phase-3 Step-2
from analysis.class_extractor import extract_classes

classes = extract_classes(ast_tree, file_path)
class_methods = {
    cls["name"]: set(cls["methods"])
    for cls in classes
}
resolved = resolve_calls(calls, local_function_names, imports,class_methods)

for r in resolved:
    print(r)




