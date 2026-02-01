import logging
from typing import List, Dict, Any
from backend.app.rag import store
from backend.app.core import config

logger = logging.getLogger(__name__)

def retrieve(query: str) -> Dict[str, Any]:
    """Dynamic retrieval with threshold-based refusal support."""
    if not query.strip():
        return {"chunks": []}

    collection = store.get_collection()
    model = store._get_model()

    query_embedding = model.encode(query, convert_to_tensor=False).tolist()

    try:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=config.CANDIDATE_K,
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

    # Threshold filtering
    filtered_candidates = [c for c in candidates if c['score'] >= config.MIN_SCORE_THRESHOLD]
    
    if not filtered_candidates:
        top_score = candidates[0]['score'] if candidates else 0.0
        logger.info(f"Refusal: No chunks above threshold {config.MIN_SCORE_THRESHOLD}. Top score: {top_score:.3f}")
        return {"chunks": []}

    filtered_candidates.sort(key=lambda x: x['score'], reverse=True)

    # Variable K via drop-off detection
    final_chunks = []
    if filtered_candidates:
        final_chunks.append(filtered_candidates[0])
        
        for i in range(1, len(filtered_candidates)):
            prev_score = filtered_candidates[i-1]['score']
            current_score = filtered_candidates[i]['score']
            drop = prev_score - current_score
            
            if drop > config.DROP_OFF_THRESHOLD:
                logger.info(f"Drop-off detected: {drop:.3f} at rank {i}. Stopping.")
                break
            
            final_chunks.append(filtered_candidates[i])

    logger.info(f"Query: '{query}' | Candidates: {len(candidates)} | Valid: {len(final_chunks)}")
    
    return {"chunks": final_chunks}