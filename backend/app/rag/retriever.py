import logging
from typing import List, Dict, Any, Optional
from backend.app.rag import store
from backend.app.core import config

logger = logging.getLogger(__name__)


def retrieve(
    query: str,
    top_k: Optional[int] = None,
    min_similarity: Optional[float] = None,
    diverse_sampling: bool = False,
) -> Dict[str, Any]:
    """
    Intent-aware retrieval with configurable strategies.
    
    Args:
        query: Search query
        top_k: Number of chunks to retrieve (overrides config)
        min_similarity: Minimum similarity threshold (None = no threshold)
        diverse_sampling: Sample across different documents
        
    Returns:
        Dict with 'chunks' key containing retrieved results
    """
    if not query.strip():
        return {"chunks": []}

    collection = store.get_collection()
    model = store._get_model()

    query_embedding = model.encode(query, convert_to_tensor=False).tolist()

    # Use config defaults if not specified
    candidate_k = top_k or config.CANDIDATE_K
    
    try:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=candidate_k,
            include=["documents", "metadatas", "distances"]
        )
    except Exception as e:
        logger.error(f"ChromaDB query failed: {e}")
        return {"chunks": []}

    if not results['ids'] or not results['ids'][0]:
        logger.info("No documents found in DB.")
        return {"chunks": []}

    distances = results['distances'][0]
    documents = results['documents'][0]
    metadatas = results['metadatas'][0]
    
    # Convert L2 distance to cosine similarity: score = 1 - (L2^2 / 2)
    candidates = []
    for i in range(len(distances)):
        dist = distances[i]
        score = 1 - (dist**2 / 2)
        
        candidates.append({
            "text": documents[i],
            "metadata": metadatas[i],
            "score": score
        })

    # Apply similarity threshold if specified
    if min_similarity is not None:
        filtered_candidates = [c for c in candidates if c['score'] >= min_similarity]
        
        if not filtered_candidates:
            top_score = candidates[0]['score'] if candidates else 0.0
            logger.info(f"Refusal: No chunks above threshold {min_similarity}. Top score: {top_score:.3f}")
            return {"chunks": []}
    else:
        # No threshold - use all candidates (summary/description mode)
        filtered_candidates = candidates

    filtered_candidates.sort(key=lambda x: x['score'], reverse=True)

    # Diverse sampling: prefer chunks from different documents
    if diverse_sampling:
        final_chunks = _diverse_sample(filtered_candidates, top_k or 10)
    else:
        # Standard mode with drop-off detection
        final_chunks = _apply_dropoff(filtered_candidates)

    logger.info(f"Query: '{query}' | Candidates: {len(candidates)} | Retrieved: {len(final_chunks)}")
    
    return {"chunks": final_chunks}


def _apply_dropoff(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Apply drop-off detection to filter candidates."""
    if not candidates:
        return []
    
    final_chunks = [candidates[0]]
    
    for i in range(1, len(candidates)):
        prev_score = candidates[i-1]['score']
        current_score = candidates[i]['score']
        drop = prev_score - current_score
        
        if drop > config.DROP_OFF_THRESHOLD:
            logger.info(f"Drop-off detected: {drop:.3f} at rank {i}. Stopping.")
            break
        
        final_chunks.append(candidates[i])
    
    return final_chunks


def _diverse_sample(candidates: List[Dict[str, Any]], max_chunks: int) -> List[Dict[str, Any]]:
    """Sample chunks from diverse documents."""
    if not candidates:
        return []
    
    # Group by filename
    by_file = {}
    for chunk in candidates:
        filename = chunk['metadata'].get('filename', 'unknown')
        if filename not in by_file:
            by_file[filename] = []
        by_file[filename].append(chunk)
    
    # Round-robin sampling across files
    selected = []
    file_keys = list(by_file.keys())
    idx = 0
    
    while len(selected) < max_chunks:
        file_key = file_keys[idx % len(file_keys)]
        if by_file[file_key]:
            selected.append(by_file[file_key].pop(0))
        
        idx += 1
        
        # Stop if all files exhausted
        if all(len(chunks) == 0 for chunks in by_file.values()):
            break
    
    logger.info(f"Diverse sampling: {len(selected)} chunks from {len(by_file)} documents")
    return selected