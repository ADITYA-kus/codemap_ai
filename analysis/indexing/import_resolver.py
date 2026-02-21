# Resolves imports → actual files
from dataclasses import dataclass
from typing import Dict, Optional, List

from analysis.indexing.symbol_index import SymbolIndex


# ----------------------------
# Data Model
# ----------------------------

@dataclass
class ResolvedImport:
    """
    Represents a resolved import in a single file.
    """
    alias: str                 # local name used in file
    module: str                # full module path
    symbol: Optional[str]      # imported symbol (None for plain import)


# ----------------------------
# Import Resolver
# ----------------------------

class ImportResolver:
    """
    Resolves raw import statements into fully-qualified references.
    Also stores per-module resolved import maps for later lookup.
    """

    def __init__(self, symbol_index: SymbolIndex):
        self.symbol_index = symbol_index
        # ✅ NEW: cache { module_name -> { alias -> ResolvedImport } }
        self._imports_by_module: Dict[str, Dict[str, ResolvedImport]] = {}

    # ----------------------------
    # Public API
    # ----------------------------
    def resolve_imports(
        self,
        imports: List[dict],
        current_module: str
    ) -> Dict[str, ResolvedImport]:
        """
        Resolves all imports for a single file.

        Returns:
            Dict[alias -> ResolvedImport]
        """
        resolved: Dict[str, ResolvedImport] = {}

        for imp in imports:
            if imp["type"] == "import":
                self._handle_import(imp, resolved)

            elif imp["type"] == "from_import":
                self._handle_from_import(imp, current_module, resolved)

        return resolved

    def index_module_imports(self, module_name: str, imports: List[dict]) -> Dict[str, ResolvedImport]:
        """
        ✅ NEW: Resolve and store imports for a module.
        This is what your runner should call once per file.
        """
        resolved = self.resolve_imports(imports, module_name)
        self._imports_by_module[module_name] = resolved
        return resolved

    def get_imports(self, module_name: str) -> Dict[str, ResolvedImport]:
        """
        ✅ NEW: Fetch resolved import map for a module.
        Returns empty dict if module was never indexed.
        """
        return self._imports_by_module.get(module_name, {})

    def clear_module(self, module_name: str):
        """
        ✅ Optional helper: remove cached imports for one module.
        Useful later for incremental indexing in VS Code.
        """
        if module_name in self._imports_by_module:
            del self._imports_by_module[module_name]

    def clear(self):
        """
        ✅ Optional helper: clears all cached imports.
        """
        self._imports_by_module.clear()

    # ----------------------------
    # Internal Helpers
    # ----------------------------
    def _handle_import(self, imp: dict, resolved: Dict[str, ResolvedImport]):
        """
        Handles: import a.b.c as x
        """
        module = imp["module"]
        alias = imp["alias"] if imp.get("alias") else module.split(".")[-1]

        resolved[alias] = ResolvedImport(
            alias=alias,
            module=module,
            symbol=None
        )

    def _handle_from_import(
        self,
        imp: dict,
        current_module: str,
        resolved: Dict[str, ResolvedImport]
    ):
        """
        Handles: from a.b import c as d
        Also supports relative imports.
        """
        base_module = imp["module"]
        name = imp["name"]
        alias = imp["alias"] if imp.get("alias") else name
        level = imp.get("level", 0)

        # Resolve relative imports
        if level > 0:
            base_module = self._resolve_relative_module(
                current_module=current_module,
                level=level,
                target_module=base_module
            )

        resolved[alias] = ResolvedImport(
            alias=alias,
            module=base_module,
            symbol=name
        )

    def _resolve_relative_module(
        self,
        current_module: str,
        level: int,
        target_module: Optional[str]
    ) -> str:
        """
        Resolves relative imports like:
        from ..utils import helper
        """
        parts = current_module.split(".")

        if level > len(parts):
            return target_module or ""

        base = parts[:-level]
        if target_module:
            return ".".join(base + [target_module])

        return ".".join(base)
