import logging
from typing import List, Dict, Any, Optional
import threading
import chromadb
from sentence_transformers import SentenceTransformer
from chromadb.errors import NotFoundError
from backend.app.core import config

logger = logging.getLogger(__name__)

_client: Optional[chromadb.PersistentClient] = None
_collection: Optional[chromadb.Collection] = None
_model: Optional[SentenceTransformer] = None
_lock = threading.Lock()  # Thread-safe access

# Batching configuration
BATCH_SIZE = 500  # Process up to 500 chunks at a time to prevent OOM

def _get_model() -> SentenceTransformer:
    """Lazy load embedding model."""
    global _model
    if _model is None:
        logger.info(f"Loading embedding model: {config.EMBEDDING_MODEL}")
        _model = SentenceTransformer(config.EMBEDDING_MODEL, device='cpu')
    return _model

def _get_db_client() -> chromadb.PersistentClient:
    """Lazy load ChromaDB client."""
    global _client
    if _client is None:
        logger.info(f"Initializing Vector DB at: {config.DB_PATH}")
        import os
        os.makedirs(config.DB_PATH, exist_ok=True)
        _client = chromadb.PersistentClient(path=config.DB_PATH)
    return _client

def get_collection() -> chromadb.Collection:
    """Return active Chroma collection, creating if needed."""
    global _collection
    client = _get_db_client()
    
    if _collection is None:
        _collection = client.get_or_create_collection(name=config.COLLECTION_NAME)
    
    return _collection

def index_chunks(chunks: List[Dict[str, Any]]) -> None:
    """
    Embed and store chunks in vector database with batching.
    Thread-safe with batching to prevent OOM on large datasets.
    """
    if not chunks:
        logger.warning("No chunks provided to index.")
        return

    logger.info(f"Preparing to index {len(chunks)} chunks...")
    
    with _lock:
        collection = get_collection()
        model = _get_model()

        total_indexed = 0
        
        # Process in batches
        for batch_start in range(0, len(chunks), BATCH_SIZE):
            batch_end = min(batch_start + BATCH_SIZE, len(chunks))
            batch = chunks[batch_start:batch_end]
            
            logger.info(f"Processing batch {batch_start + 1}-{batch_end} of {len(chunks)}")
            
            ids = []
            documents = []
            metadatas = []
            
            for chunk in batch:
                chunk_text = chunk.get("text", "")
                if not chunk_text.strip():
                    continue
                    
                chunk_meta = chunk.get("metadata", {}).copy()
                chunk_id = chunk_meta.get("chunk_id")
                
                if not chunk_id:
                    logger.warning("Skipping chunk without ID.")
                    continue

                # ChromaDB requires non-None values
                safe_meta = {}
                for k, v in chunk_meta.items():
                    if v is None:
                        if k in ["page", "line_start", "line_end"]:
                            safe_meta[k] = -1
                        else:
                            safe_meta[k] = ""
                    else:
                        safe_meta[k] = v

                ids.append(chunk_id)
                documents.append(chunk_text)
                metadatas.append(safe_meta)

            if not ids:
                continue

            # Generate Embeddings for batch
            logger.info(f"Generating embeddings for {len(documents)} documents...")
            embeddings = model.encode(documents, convert_to_tensor=False, show_progress_bar=True).tolist()

            logger.info(f"Upserting {len(ids)} chunks to Vector DB...")
            collection.upsert(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas
            )
            
            total_indexed += len(ids)
        
        logger.info(f"Indexing complete. Total indexed: {total_indexed}")


def clear_index():
    """Delete vector collection and reset. Thread-safe."""
    with _lock:
        client = _get_db_client()
        global _collection
        try:
            client.delete_collection(config.COLLECTION_NAME)
            _collection = None
            logger.info("Index cleared.")
        except NotFoundError:
            logger.info("No existing collection to clear.")