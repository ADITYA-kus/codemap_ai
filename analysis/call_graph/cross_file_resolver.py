# Cross-file call resolution
from typing import Optional

from analysis.indexing.symbol_index import SymbolIndex, SymbolInfo, SymbolKind
from analysis.indexing.import_resolver import ImportResolver, ResolvedImport


class CrossFileResolver:
    """
    Resolves a function/method call to its exact SymbolInfo
    using symbol index and import resolver.
    """

    def __init__(
        self,
        symbol_index: SymbolIndex,
        import_resolver: ImportResolver
    ):
        self.symbol_index = symbol_index
        self.import_resolver = import_resolver  # ✅ NOW ACTUALLY USED

    # -------------------------------------------------
    # Public API
    # -------------------------------------------------
    def resolve_call(
        self,
        call: dict,
        current_module: str
    ) -> Optional[SymbolInfo]:

        callee = call["callee"]
        obj = call.get("object")
        class_name = call.get("class")

        # 🔹 Get imports for this module
        import_map = self.import_resolver.get_imports(current_module)

        # 1️⃣ Method call on self
        if obj == "self" and class_name:
            symbol = self._resolve_method(
                current_module, class_name, callee
            )
            if symbol:
                return symbol

        # 2️⃣ Local function
        symbol = self._resolve_local_function(
            current_module, callee
        )
        if symbol:
            return symbol

        # 3️⃣ Imported symbol (direct)
        if callee in import_map:
            symbol = self._resolve_imported_symbol(
                import_map[callee]
            )
            if symbol:
                return symbol

        # 4️⃣ Imported module attribute
        if obj and obj in import_map:
            symbol = self._resolve_module_attribute(
                import_map[obj], callee
            )
            if symbol:
                return symbol

        # 5️⃣ Built-in
        import builtins 
        if hasattr(builtins,callee):
            return SymbolInfo(
                name=callee,
                qualified_name=callee,
                kind=SymbolKind.BUILTIN,
                module="builtins",
                file_path="",
                start_line=-1,
                end_line=-1
            )

        return None

    # -------------------------------------------------
    # Helpers
    # -------------------------------------------------

    def _resolve_method(
        self,
        module: str,
        class_name: str,
        method_name: str
    ) -> Optional[SymbolInfo]:
        return self.symbol_index.get(
            module, f"{class_name}.{method_name}"
        )

    def _resolve_local_function(
        self,
        module: str,
        function_name: str
    ) -> Optional[SymbolInfo]:
        return self.symbol_index.get(module, function_name)

    def _resolve_imported_symbol(
        self,
        resolved: ResolvedImport
    ) -> Optional[SymbolInfo]:
        if resolved.symbol:
            return self.symbol_index.get(
                resolved.module, resolved.symbol
            )
        return None

    def _resolve_module_attribute(
        self,
        resolved: ResolvedImport,
        attr: str
    ) -> Optional[SymbolInfo]:
        return self.symbol_index.get(
            resolved.module, attr
        )
