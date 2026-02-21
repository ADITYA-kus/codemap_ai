from analysis.indexing.symbol_index import SymbolIndex, SymbolInfo, SymbolKind
from analysis.indexing.import_resolver import ImportResolver
from analysis.call_graph.cross_file_resolver import CrossFileResolver

from analysis.core.function_extractor import extract_functions
from analysis.core.class_extractor import extract_classes
from analysis.call_graph.call_extractor import extract_function_calls
from analysis.core.import_extractor import extract_imports
from analysis.core.ast_parser import parse_python_file


# ---- SETUP ----
file_path = r"analysis\core\test.py"
current_module = "analysis.core.test"

tree = parse_python_file(file_path)

functions = extract_functions(tree, file_path)
classes = extract_classes(tree, file_path)
calls = extract_function_calls(file_path)
imports = extract_imports(file_path)


# ---- BUILD SYMBOL INDEX ----
symbol_index = SymbolIndex()

for f in functions:
    symbol_index.add_symbol(SymbolInfo(
        name=f["fun_name"],
        qualified_name=f["fun_name"],
        kind=SymbolKind.FUNCTION,
        module=current_module,
        file_path=f["file_name"],
        start_line=f["start_line"],
        end_line=f["end_line"]
    ))

for cls in classes:
    symbol_index.add_symbol(SymbolInfo(
        name=cls["name"],
        qualified_name=cls["name"],
        kind=SymbolKind.CLASS,
        module=current_module,
        file_path=cls["file"],
        start_line=cls["start_line"],
        end_line=cls["end_line"]
    ))


# ---- RESOLVE IMPORTS ----
import_resolver = ImportResolver(symbol_index)
import_map = import_resolver.resolve_imports(imports, current_module)


# ---- RESOLVE CALLS ---
resolver = CrossFileResolver(symbol_index)

print("\nResolved Calls:\n")

for call in calls:
    symbol = resolver.resolve_call(call, import_map, current_module)
    print(
        f"{call['caller']} -> {call['callee']}  ==>  "
        f"{symbol.qualified_name if symbol else 'UNRESOLVED'}"
    )
