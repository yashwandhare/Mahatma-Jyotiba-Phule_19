import os
import logging
import hashlib
from typing import List, Dict, Optional, Any
from pypdf import PdfReader

logger = logging.getLogger(__name__)

EXT_PDF = {'.pdf'}
EXT_TEXT = {'.txt', '.md', '.markdown'}
EXT_CODE = {'.py', '.js', '.java', '.ts', '.cpp', '.c', '.h', '.html', '.css', '.json', '.yaml', '.yml', '.sh'}
LINES_PER_SEGMENT = 50

def load_files(folder_path: str) -> List[Dict[str, Any]]:
    """Scan folder recursively and extract text with metadata."""
    documents = []
    
    if not os.path.isdir(folder_path):
        logger.error(f"Invalid directory path: {folder_path}")
        return []

    logger.info(f"Scanning directory: {folder_path}")

    for root, dirs, files in os.walk(folder_path):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        
        for file in files:
            if file.startswith('.'):
                continue
                
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, folder_path)
            
            _, ext = os.path.splitext(file)
            ext = ext.lower()

            try:
                if ext in EXT_PDF:
                    docs = _process_pdf(file_path, rel_path)
                    documents.extend(docs)
                elif ext in EXT_TEXT:
                    docs = _process_text_or_code(file_path, rel_path, "text")
                    documents.extend(docs)
                elif ext in EXT_CODE:
                    docs = _process_text_or_code(file_path, rel_path, "code")
                    documents.extend(docs)
            except Exception as e:
                logger.error(f"Failed to process {rel_path}: {str(e)}")

    logger.info(f"Loaded {len(documents)} document segments from {folder_path}")
    return documents

def _process_pdf(file_path: str, rel_path: str) -> List[Dict[str, Any]]:
    """Extracts text from PDF page by page."""
    docs = []
    try:
        reader = PdfReader(file_path)
        for i, page_obj in enumerate(reader.pages):
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