from analysis.indexing.import_resolver import ImportResolver
from analysis.indexing.symbol_index import SymbolIndex, SymbolInfo, SymbolKind
from analysis.core.import_extractor import extract_imports


# ---- SETUP ----
file_path = r"analysis\core\test.py"
current_module = "analysis.core.test" # same file but in moule form

imports = extract_imports(file_path)

symbol_index = SymbolIndex()
resolver = ImportResolver(symbol_index)


# ---- RUN ----
import_map = resolver.resolve_imports(imports, current_module)


# ---- OUTPUT ----
print("\nResolved Imports:\n")
for alias, resolved in import_map.items():
    print(f"{alias}  ->  module={resolved.module}, symbol={resolved.symbol}")
