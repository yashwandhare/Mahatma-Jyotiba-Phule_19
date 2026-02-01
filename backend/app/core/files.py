"""Centralized file handling and validation."""

import logging
import os
from pathlib import Path
from typing import List, Set, Tuple

logger = logging.getLogger(__name__)

# Supported file extensions
SUPPORTED_EXTENSIONS: Set[str] = {
    '.pdf',
    '.txt', '.md', '.markdown',
    '.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.hpp',
    '.html', '.css', '.json', '.yaml', '.yml', '.xml',
    '.sh', '.bash', '.zsh',
    '.rs', '.go', '.rb', '.php',
}

# File size limits
MAX_FILE_SIZE_MB = 50
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


class FileValidationError(Exception):
    """File validation failed."""
    pass


def is_supported_file(filepath: str) -> bool:
    """Check if file extension is supported."""
    return Path(filepath).suffix.lower() in SUPPORTED_EXTENSIONS


def validate_file_size(filepath: str) -> Tuple[bool, str]:
    """
    Validate file size is within limits.
    
    Returns:
        (is_valid, error_message)
    """
    try:
        size = os.path.getsize(filepath)
        if size > MAX_FILE_SIZE_BYTES:
            size_mb = size / (1024 * 1024)
            return False, f"File too large: {size_mb:.1f}MB (max: {MAX_FILE_SIZE_MB}MB)"
        return True, ""
    except Exception as e:
        return False, f"Cannot check file size: {e}"


def validate_file(filepath: str) -> Tuple[bool, str]:
    """
    Validate a single file.
    
    Returns:
        (is_valid, error_message)
    """
    if not os.path.exists(filepath):
        return False, "File does not exist"
    
    if not os.path.isfile(filepath):
        return False, "Path is not a file"
    
    if not os.access(filepath, os.R_OK):
        return False, "File is not readable"
    
    if not is_supported_file(filepath):
        ext = Path(filepath).suffix or "(no extension)"
        return False, f"Unsupported file type: {ext}"
    
    return validate_file_size(filepath)


def collect_files(path: str, recursive: bool = True) -> List[str]:
    """
    Collect all supported files from a path (file or directory).
    
    Args:
        path: File or directory path
        recursive: If directory, recursively collect files
        
    Returns:
        List of valid file paths
    """
    path_obj = Path(path)
    
    if not path_obj.exists():
        logger.warning(f"Path does not exist: {path}")
        return []
    
    if path_obj.is_file():
        is_valid, error = validate_file(str(path_obj))
        if is_valid:
            return [str(path_obj)]
        else:
            logger.warning(f"Skipping {path}: {error}")
            return []
    
    if path_obj.is_dir():
        files = []
        pattern = "**/*" if recursive else "*"
        
        for item in path_obj.glob(pattern):
            if item.is_file():
                # Skip hidden files
                if item.name.startswith('.'):
                    continue
                
                is_valid, error = validate_file(str(item))
                if is_valid:
                    files.append(str(item))
                else:
                    logger.debug(f"Skipping {item}: {error}")
        
        return files
    
    return []


def validate_paths(paths: List[str]) -> Tuple[List[str], List[str]]:
    """
    Validate and collect files from multiple paths.
    
    Args:
        paths: List of file or directory paths
        
    Returns:
        (valid_files, errors) tuple
        valid_files: List of validated file paths
        errors: List of error messages
    """
    valid_files = []
    errors = []
    
    for path in paths:
        try:
            collected = collect_files(path)
            valid_files.extend(collected)
        except Exception as e:
            errors.append(f"Error processing {path}: {e}")
    
    return valid_files, errors


def get_supported_extensions_str() -> str:
    """Get human-readable list of supported extensions."""
    return ", ".join(sorted(SUPPORTED_EXTENSIONS))
