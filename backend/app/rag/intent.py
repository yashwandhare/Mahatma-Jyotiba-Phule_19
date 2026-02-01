"""Query intent detection for RAG pipeline."""

import re
import logging
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class QueryIntent(str, Enum):
    """Query intent types for retrieval strategies."""
    FACTUAL = "factual"
    SUMMARY = "summary"
    DESCRIPTION = "description"


# Intent detection patterns (ordered by specificity)
_INTENT_PATTERNS = [
    # Description patterns - what is this document about
    (QueryIntent.DESCRIPTION, [
        r"\bwhat\s+(?:is|are)\s+(?:this|these|the)\s+(?:document|file|paper|article|text)s?\s+about\b",
        r"\b(?:describe|explain)\s+(?:this|these|the)\s+(?:document|file|paper)s?\b",
        r"\bwhat\s+(?:does|do)\s+(?:this|these|the)\s+(?:document|file|paper)s?\s+(?:cover|discuss|contain)\b",
        r"\b(?:overview|outline)\s+of\s+(?:this|these|the)\s+(?:document|file)s?\b",
        r"\btell\s+me\s+about\s+(?:this|these|the)\s+(?:document|file)s?\b",
    ]),
    
    # Summary patterns - summarize content
    (QueryIntent.SUMMARY, [
        r"\b(?:summarize|summary)\b",
        r"\bgive\s+(?:me\s+)?(?:a|an)\s+(?:brief\s+)?(?:summary|overview)\b",
        r"\bwhat\s+(?:are|is)\s+the\s+(?:main|key)\s+(?:points|ideas|concepts|topics)\b",
        r"\b(?:overview|outline)\s+of\b",
        r"\blist\s+(?:all|the)\s+(?:topics|sections|chapters|key\s+points)\b",
        r"\bhigh-?level\s+(?:summary|overview)\b",
        r"\bin\s+brief\b",
    ]),
]


def detect_intent(query: str) -> QueryIntent:
    """
    Detect query intent using pattern matching.
    
    Args:
        query: User query string
        
    Returns:
        QueryIntent enum value
        
    Strategy:
    - DESCRIPTION: "what is this document about", "describe this file"
    - SUMMARY: "summarize", "give overview", "what are main points"
    - FACTUAL: Default for specific questions
    """
    query_lower = query.lower().strip()
    
    # Check patterns in order of specificity
    for intent, patterns in _INTENT_PATTERNS:
        for pattern in patterns:
            if re.search(pattern, query_lower, re.IGNORECASE):
                logger.info(f"Intent detected: {intent.value} (pattern: {pattern[:50]}...)")
                return intent
    
    # Default to factual for specific questions
    logger.info(f"Intent detected: {QueryIntent.FACTUAL.value} (default)")
    return QueryIntent.FACTUAL


def get_retrieval_strategy(intent: QueryIntent) -> dict:
    """
    Get retrieval configuration for given intent.
    
    Returns dict with:
    - top_k: Number of chunks to retrieve
    - min_similarity: Minimum similarity threshold (None = no threshold)
    - diverse_sampling: Whether to sample across documents
    - strict_refusal: Whether to refuse if no answer found
    """
    if intent == QueryIntent.FACTUAL:
        return {
            "top_k": 5,
            "min_similarity": 0.5,
            "diverse_sampling": False,
            "strict_refusal": True,
        }
    
    elif intent == QueryIntent.SUMMARY:
        return {
            "top_k": 10,
            "min_similarity": None,  # No threshold, get representative chunks
            "diverse_sampling": True,  # Sample across documents
            "strict_refusal": False,
        }
    
    elif intent == QueryIntent.DESCRIPTION:
        return {
            "top_k": 8,
            "min_similarity": None,
            "diverse_sampling": True,
            "strict_refusal": False,
        }
    
    # Fallback (shouldn't happen)
    return {
        "top_k": 5,
        "min_similarity": 0.5,
        "diverse_sampling": False,
        "strict_refusal": True,
    }
