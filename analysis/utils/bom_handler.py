"""BOM (Byte Order Mark) handling utilities for CodeMap.

This module provides utilities to handle UTF-8 BOM characters that are
sometimes added to Python files by certain editors (especially on Windows).

BOM (U+FEFF) is an invisible character that Python's AST parser cannot handle,
causing: "invalid non-printable character U+FEFF"

Solution: Strip BOM before parsing Python files.
"""


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


def read_source_file(file_path: str) -> str:
    """Read a Python file and remove BOM if present.
    
    This is a convenience function that combines file reading with BOM removal.
    
    Args:
        file_path: Path to Python file to read
        
    Returns:
        Source code with BOM removed
        
    Raises:
        FileNotFoundError: If file doesn't exist
        UnicodeDecodeError: If file encoding is not UTF-8
    """
    with open(file_path, "r", encoding="utf-8") as f:
        source = f.read()
    return remove_bom(source)
