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


def collect_valid_files(paths: List[str]) -> Tuple[List[str], List[str]]:
    """Collect and validate files from mixed file/dir inputs.

    Returns (valid_files, errors) where errors are human-readable messages.
    No exceptions are raised for per-file issues; filesystem failures are captured as errors.
    """
    valid_files: List[str] = []
    errors: List[str] = []
    seen_files: Set[str] = set()

    for raw_path in paths or []:
        if not raw_path or not str(raw_path).strip():
            continue

        try:
            path_obj = Path(raw_path).expanduser().resolve()
        except Exception as exc:  # Resolution issues
            errors.append(f"{raw_path}: invalid path ({exc})")
            continue

        if not path_obj.exists():
            errors.append(f"{path_obj}: not found")
            continue

        if path_obj.is_file():
            canonical = str(path_obj)
            if canonical in seen_files:
                logger.debug("Skipping duplicate file input: %s", canonical)
                continue
            is_valid, error = validate_file(canonical)
            if is_valid:
                valid_files.append(canonical)
                seen_files.add(canonical)
            else:
                errors.append(f"{path_obj}: {error}")
            continue

        if path_obj.is_dir():
            try:
                for item in path_obj.rglob("*"):
                    if not item.is_file():
                        continue
                    if item.name.startswith('.'):
                        continue
                    canonical = str(item.resolve())
                    if canonical in seen_files:
                        logger.debug("Skipping duplicate file input: %s", canonical)
                        continue
                    is_valid, error = validate_file(canonical)
                    if is_valid:
                        valid_files.append(canonical)
                        seen_files.add(canonical)
                    else:
                        errors.append(f"{item}: {error}")
            except Exception as exc:
                errors.append(f"{path_obj}: failed to scan directory ({exc})")
            continue

        errors.append(f"{path_obj}: unsupported path type")

    return valid_files, errors


def get_supported_extensions_str() -> str:
    """Get human-readable list of supported extensions."""
    return ", ".join(sorted(SUPPORTED_EXTENSIONS))
