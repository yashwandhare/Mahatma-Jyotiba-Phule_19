import hashlib
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class Chunker:
    """Splits documents into overlapping chunks for retrieval."""
    def __init__(self, chunk_size: int = 2000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = ["\n\n", "\n", " ", ""]

    def chunk(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process documents and return chunks with preserved metadata."""
        all_chunks = []
        
        if not documents:
            logger.warning("No documents provided for chunking.")
            return []
        
        logger.info(f"Chunking {len(documents)} documents with size={self.chunk_size}, overlap={self.chunk_overlap}")

        for doc in documents:
            text = doc.get("text", "")
            metadata = doc.get("metadata", {})
            
            if not text or not text.strip():
                continue

            text_chunks = self._split_text(text)

            for i, chunk_text in enumerate(text_chunks):
                if not chunk_text.strip():
                    continue
                    
                source_id = metadata.get("doc_id", "unknown")
                chunk_id = hashlib.md5(f"{source_id}_{i}_{chunk_text[:20]}".encode()).hexdigest()

                chunk_metadata = metadata.copy()
                chunk_metadata["chunk_id"] = chunk_id
                chunk_metadata["source_doc_id"] = source_id

                all_chunks.append({
                    "text": chunk_text,
                    "metadata": chunk_metadata
                })

        logger.info(f"Generated {len(all_chunks)} chunks")
        return all_chunks

    def _split_text(self, text: str) -> List[str]:
        """Recursively split text by separators to fit chunk_size."""
        final_chunks = []
        if len(text) <= self.chunk_size:
            return [text]

        separator = ""
        for sep in self.separators:
            if sep in text:
                separator = sep
                break
        
        if separator:
            splits = text.split(separator)
        else:
            splits = list(text)

        current_chunk = []
        current_length = 0
        
        sep_len = len(separator)

        for split in splits:
            split_len = len(split)
            
            if current_length + split_len + sep_len > self.chunk_size:
                if current_chunk:
                    full_chunk = separator.join(current_chunk)
                    final_chunks.append(full_chunk)
                    
                    # Carry forward overlap for context continuity
                    overlap_buffer = []
                    overlap_len = 0
                    for item in reversed(current_chunk):
                        if overlap_len + len(item) + sep_len <= self.chunk_overlap:
                            overlap_buffer.insert(0, item)
                            overlap_len += len(item) + sep_len
                        else:
                            break
                    current_chunk = overlap_buffer
                    current_length = overlap_len

            current_chunk.append(split)
            current_length += split_len + sep_len

        if current_chunk:
            final_chunks.append(separator.join(current_chunk))

        return final_chunks