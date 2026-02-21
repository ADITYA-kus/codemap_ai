import ast
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class SymbolKind(Enum):
    FUNCTION = "function"
    CLASS = "class"
    METHOD = "method"
    MODULE = "module"
    BUILTIN = "builtin"
    EXTERNAL = "external"


@dataclass
class SymbolInfo:
    name: str
    qualified_name: str
    kind: SymbolKind
    module: str
    file_path: str
    start_line: int
    end_line: int
    class_name: Optional[str] = None
    metadata: Dict = field(default_factory=dict)


class SymbolIndex:
    """Global registry of all symbols across the codebase."""

    def __init__(self):
        self._symbols: List[SymbolInfo] = []
        self._by_name: Dict[str, List[SymbolInfo]] = {}
        self._by_fqn: Dict[Tuple[str, str], SymbolInfo] = {}

    def add_symbol(self, symbol: SymbolInfo):
        key = (symbol.module, symbol.qualified_name)
        if key in self._by_fqn:
            return
        self._symbols.append(symbol)
        self._by_fqn[key] = symbol
        self._by_name.setdefault(symbol.name, []).append(symbol)

    def index_file(self, ast_tree: ast.AST, module: str, file_path: str):
        max_line = 1
        for node in ast.walk(ast_tree):
            ln = getattr(node, "lineno", None)
            end_ln = getattr(node, "end_lineno", None)
            if isinstance(ln, int):
                max_line = max(max_line, ln)
            if isinstance(end_ln, int):
                max_line = max(max_line, end_ln)

        self.add_symbol(
            SymbolInfo(
                name="<module>",
                qualified_name="<module>",
                kind=SymbolKind.MODULE,
                module=module,
                file_path=file_path,
                start_line=1,
                end_line=max_line,
            )
        )

        for node in ast.walk(ast_tree):
            if isinstance(node, ast.FunctionDef):
                symbol = SymbolInfo(
                    name=node.name,
                    qualified_name=node.name,
                    kind=SymbolKind.FUNCTION,
                    module=module,
                    file_path=file_path,
                    start_line=int(getattr(node, "lineno", 1) or 1),
                    end_line=int(getattr(node, "end_lineno", getattr(node, "lineno", 1)) or getattr(node, "lineno", 1)),
                )
                self.add_symbol(symbol)

            elif isinstance(node, ast.ClassDef):
                class_symbol = SymbolInfo(
                    name=node.name,
                    qualified_name=node.name,
                    kind=SymbolKind.CLASS,
                    module=module,
                    file_path=file_path,
                    start_line=int(getattr(node, "lineno", 1) or 1),
                    end_line=int(getattr(node, "end_lineno", getattr(node, "lineno", 1)) or getattr(node, "lineno", 1)),
                )
                self.add_symbol(class_symbol)

                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        method_symbol = SymbolInfo(
                            name=item.name,
                            qualified_name=f"{node.name}.{item.name}",
                            kind=SymbolKind.METHOD,
                            module=module,
                            file_path=file_path,
                            start_line=int(getattr(item, "lineno", 1) or 1),
                            end_line=int(getattr(item, "end_lineno", getattr(item, "lineno", 1)) or getattr(item, "lineno", 1)),
                            class_name=node.name,
                        )
                        self.add_symbol(method_symbol)

    def load_snapshot(self, snapshot: List[Dict]):
        self.clear()
        if not isinstance(snapshot, list):
            return
        for row in snapshot:
            if not isinstance(row, dict):
                continue
            kind_raw = str(row.get("kind", "function") or "function").lower()
            try:
                kind = SymbolKind(kind_raw)
            except Exception:
                kind = SymbolKind.FUNCTION
            sym = SymbolInfo(
                name=str(row.get("name", "") or ""),
                qualified_name=str(row.get("qualified_name", "") or ""),
                kind=kind,
                module=str(row.get("module", "") or ""),
                file_path=str(row.get("file_path", "") or ""),
                start_line=int(row.get("start_line", 1) or 1),
                end_line=int(row.get("end_line", row.get("start_line", 1)) or row.get("start_line", 1)),
                class_name=row.get("class_name"),
                metadata=row.get("metadata", {}) if isinstance(row.get("metadata"), dict) else {},
            )
            if sym.module and sym.qualified_name:
                self.add_symbol(sym)

    def get_by_name(self, name: str) -> List[SymbolInfo]:
        return self._by_name.get(name, [])

    def get(self, module: str, qualified_name: str) -> Optional[SymbolInfo]:
        return self._by_fqn.get((module, qualified_name))

    def all_symbols(self) -> List[SymbolInfo]:
        return list(self._symbols)

    def remove_by_file(self, file_path: str):
        keep = [s for s in self._symbols if s.file_path != file_path]
        self.clear()
        for s in keep:
            self.add_symbol(s)

    def clear(self):
        self._symbols.clear()
        self._by_name.clear()
        self._by_fqn.clear()
