"""BOM (Byte Order Mark), encoding, and AST parsing utilities for CodeMap.

This module provides utilities to handle:
1. UTF-8 BOM (Byte Order Mark) characters added by certain editors
2. Non-UTF-8 encoded files (e.g., Latin-1, Windows-1252)

Issues handled:
- BOM (U+FEFF): invisible character causing "invalid non-printable character U+FEFF"
- Non-UTF-8: files with different encodings causing UnicodeDecodeError

Solution: Detect encoding with fallback chain, strip BOM, and parse quietly.
"""

import ast
import warnings
from typing import Tuple


def remove_bom(source: str) -> str:
    """Remove UTF-8 BOM (Byte Order Mark) from source code if present.
    
    BOM is a special character (U+FEFF) that some editors (especially Notepad
    on Windows) add to the start of files. Python's AST parser doesn't handle it.
    
    This function silently removes it if present, or returns the source unchanged.
    
    Args:
        source: Python source code as string
        
    Returns:
        Source code with BOM removed if present
        
    Example:
        >>> source_with_bom = '\\ufeffdef hello(): pass'
        >>> clean_source = remove_bom(source_with_bom)
        >>> print(clean_source)
        def hello(): pass
    """
    if source.startswith('\ufeff'):
        return source[1:]
    return source


def detect_encoding(file_path: str) -> Tuple[str, bool]:
    """Detect file encoding by trying multiple decodings.
    
    Tries encodings in this order:
    1. UTF-8 (most common for Python files)
    2. System default encoding
    3. Latin-1 / ISO-8859-1 (accepts any byte sequence)
    
    Args:
        file_path: Path to file to detect encoding for
        
    Returns:
        Tuple of (encoding_name: str, is_fallback: bool)
        is_fallback=True means file uses non-standard encoding
        
    Raises:
        FileNotFoundError: If file doesn't exist
    """
    import sys
    
    encodings_to_try = [
        ('utf-8', False),
        (sys.getdefaultencoding(), False),
        ('latin-1', True),  # Latin-1 accepts any byte sequence
    ]
    
    for encoding, is_fallback in encodings_to_try:
        try:
            with open(file_path, 'rb') as f:
                f.read().decode(encoding)
            return (encoding, is_fallback)
        except (UnicodeDecodeError, LookupError):
            continue
    
    # Should never reach here since Latin-1 accepts all bytes
    return ('latin-1', True)


def read_source_file(file_path: str) -> str:
    """Read a Python file with automatic encoding detection and BOM removal.
    
    Handles files with different encodings gracefully by trying multiple
    decodings in order of likelihood, then falling back to Latin-1.
    
    Args:
        file_path: Path to Python file to read
        
    Returns:
        Source code with BOM removed
        
    Raises:
        FileNotFoundError: If file doesn't exist
    """
    encoding, _is_fallback = detect_encoding(file_path)
    with open(file_path, 'r', encoding=encoding, errors='replace') as f:
        source = f.read()
    return remove_bom(source)


def parse_source_to_ast(source: str, file_path: str = "<unknown>") -> ast.AST:
    """Parse source code while suppressing noisy invalid-escape warnings.

    Some user repositories contain regular string literals like ``"\\S"`` or
    ``"\\["``. Python can emit ``SyntaxWarning: invalid escape sequence`` while
    parsing those files even though analysis can continue normally. For CodeMap,
    these warnings are implementation noise, so we suppress them here.
    """
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=SyntaxWarning)
        return ast.parse(source, filename=file_path)


def read_and_parse_python_file(file_path: str) -> ast.AST:
    """Read a Python file with encoding/BOM handling and return its AST."""
    source = read_source_file(file_path)
    return parse_source_to_ast(source, file_path=file_path)
