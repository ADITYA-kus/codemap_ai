# AST Parser Module
from analysis.utils.bom_handler import read_and_parse_python_file


def parse_python_file(file_path):
    """Parse a Python file with automatic encoding and BOM handling.
    
    This function:
    1. Reads the file with automatic encoding detection (UTF-8 → Latin-1)
    2. Removes any BOM characters automatically
    3. Parses the cleaned source code
    
    Args:
        file_path: Path to Python file to parse
        
    Returns:
        ast.Module: Parsed AST tree
        
    Raises:
        SyntaxError: If source code has syntax errors
        FileNotFoundError: If file doesn't exist
        ValueError: If file encoding cannot be determined
    """
    return read_and_parse_python_file(file_path)

