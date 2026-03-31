# AST Parser Module
import ast
from analysis.utils.bom_handler import remove_bom


def parse_python_file(file_path):
    """Parse a Python file, automatically handling UTF-8 BOM.
    
    This function:
    1. Reads the file with UTF-8 encoding
    2. Removes any BOM characters automatically
    3. Parses the cleaned source code
    
    Args:
        file_path: Path to Python file to parse
        
    Returns:
        ast.Module: Parsed AST tree
        
    Raises:
        SyntaxError: If source code has syntax errors
        FileNotFoundError: If file doesn't exist
    """
    with open(file_path, "r", encoding="utf-8") as f:
        source = f.read()

    # Remove BOM if present (handles files from Windows editors, etc.)
    source = remove_bom(source)
    
    return ast.parse(source)

