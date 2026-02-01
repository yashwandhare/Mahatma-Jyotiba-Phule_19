import os
import logging
import hashlib
from typing import List, Dict, Optional, Any, Iterable, Tuple, Set
from pypdf import PdfReader
from pathlib import Path

from backend.app.core.files import collect_valid_files

logger = logging.getLogger(__name__)

EXT_PDF = {'.pdf'}
EXT_TEXT = {'.txt', '.md', '.markdown'}
EXT_CODE = {'.py', '.js', '.java', '.ts', '.cpp', '.c', '.h', '.html', '.css', '.json', '.yaml', '.yml', '.sh'}
LINES_PER_SEGMENT = 50

def load_inputs(paths: Iterable[str]) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Ingest files/folders with centralized validation.

    Returns (documents, errors) where errors list skipped files.
    """
    documents: List[Dict[str, Any]] = []
    normalized_paths: List[str] = []
    seen_inputs: Set[str] = set()

    for raw in paths or []:
        if not raw or not str(raw).strip():
            continue
        normalized = str(raw).strip()
        if normalized in seen_inputs:
            logger.info("Skipping duplicate input path: %s", normalized)
            continue
        seen_inputs.add(normalized)
        normalized_paths.append(normalized)

    if not normalized_paths:
        logger.error("No input paths provided.")
        return [], ["No input paths provided"]

    valid_files, errors = collect_valid_files(normalized_paths)

    if not valid_files:
        logger.error("No valid files after validation.")
        return [], errors

    resolved_inputs = []
    for raw in normalized_paths:
        try:
            resolved_inputs.append(Path(raw).expanduser().resolve())
        except Exception:
            continue

    for file_path in valid_files:
        file_path_obj = Path(file_path).resolve()

        base_path = file_path_obj.parent
        for root in resolved_inputs:
            try:
                file_path_obj.relative_to(root)
                base_path = root
                break
            except ValueError:
                continue

        documents.extend(_load_file(str(file_path_obj), base_path=str(base_path)))

    logger.info(f"Loaded {len(documents)} document segments from {len(valid_files)} validated files")
    return documents, errors


def _load_file(file_path: str, base_path: str) -> List[Dict[str, Any]]:
    documents: List[Dict[str, Any]] = []
    rel_path = os.path.relpath(file_path, base_path)

    _, ext = os.path.splitext(file_path)
    ext = ext.lower()

    if ext in EXT_PDF:
        docs = _process_pdf(file_path, rel_path)
        documents.extend(docs)
    elif ext in EXT_TEXT:
        docs = _process_text_or_code(file_path, rel_path, "text")
        documents.extend(docs)
    elif ext in EXT_CODE:
        docs = _process_text_or_code(file_path, rel_path, "code")
        documents.extend(docs)
    else:
        logger.debug(f"Skipping unsupported file type: {rel_path}")

    return documents

def _process_pdf(file_path: str, rel_path: str) -> List[Dict[str, Any]]:
    """Extracts text from PDF page by page."""
    docs = []
    try:
        reader = PdfReader(file_path)
        if not reader.pages:
            logger.warning(f"PDF has no pages: {rel_path}")
            return []
            
        for i, page_obj in enumerate(reader.pages):
            try:
                text = page_obj.extract_text()
                if text and text.strip():
                    page_num = i + 1
                    doc_id = _generate_doc_id(rel_path, page=page_num)
                    docs.append({
                        "text": text,
                        "metadata": {
                            "doc_id": doc_id,
                            "filename": rel_path,
                            "file_type": "pdf",
                            "page": page_num,
                            "line_start": None,
                            "line_end": None
                        }
                    })
            except Exception as e:
                logger.warning(f"Failed to extract page {i+1} from {rel_path}: {e}")
                continue
    except Exception as e:
        logger.error(f"Error reading PDF {rel_path}: {e}")
    return docs

def _process_text_or_code(file_path: str, rel_path: str, file_type: str) -> List[Dict[str, Any]]:
    """Split file into line-based segments for traceability."""
    docs = []
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            
        total_lines = len(lines)
        if total_lines == 0:
            return []

        for i in range(0, total_lines, LINES_PER_SEGMENT):
            chunk_lines = lines[i : i + LINES_PER_SEGMENT]
            text_content = "".join(chunk_lines)
            
            if not text_content.strip():
                continue
                
            start_line = i + 1
            end_line = i + len(chunk_lines)
            doc_id = _generate_doc_id(rel_path, line_start=start_line)

            docs.append({
                "text": text_content,
                "metadata": {
                    "doc_id": doc_id,
                    "filename": rel_path,
                    "file_type": file_type,
                    "page": None,
                    "line_start": start_line,
                    "line_end": end_line
                }
            })
            
    except Exception as e:
        logger.error(f"Error reading {file_type} file {rel_path}: {e}")
    return docs

def _generate_doc_id(filename: str, page: Optional[int] = None, line_start: Optional[int] = None) -> str:
    """Stable hash for document segment."""
    unique_str = f"{filename}_{page}_{line_start}"
    return hashlib.md5(unique_str.encode()).hexdigest()