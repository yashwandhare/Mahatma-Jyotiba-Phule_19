"""Answer generation with LLM orchestration and intent-aware prompts."""

import logging
from typing import List, Dict, Any, Optional

from backend.app.core import config
from backend.app.rag.orchestrator import get_orchestrator, ProviderUnavailable, ProviderTimeout
from backend.app.rag.intent import QueryIntent
from backend.app.core.errors import get_error_message

logger = logging.getLogger(__name__)


def _build_context(retrieved_chunks: List[Dict[str, Any]]) -> str:
    """Build context string from retrieved chunks."""
    context_text = ""
    for i, chunk in enumerate(retrieved_chunks):
        text = chunk.get("text", "").strip()
        context_text += f"--- CHUNK {i+1} ---\n{text}\n\n"
    return context_text


def _collect_sources(retrieved_chunks: List[Dict[str, Any]]) -> List[str]:
    """Extract unique source references from chunks."""
    unique_sources = set()
    for chunk in retrieved_chunks:
        meta = chunk.get("metadata", {})
        filename = meta.get("filename", "unknown")

        if meta.get("page") is not None and meta.get("page") != -1:
            loc = f"page {meta['page']}"
        elif meta.get("line_start") is not None and meta.get("line_start") != -1:
            loc = f"lines {meta['line_start']}-{meta.get('line_end', '?')}"
        else:
            loc = "unknown location"

        unique_sources.add(f"{filename} ({loc})")

    return sorted(list(unique_sources))


def _system_prompt(intent: QueryIntent) -> str:
    """Get system prompt based on query intent."""
    if intent == QueryIntent.FACTUAL:
        return (
            "You are RAGex, a precise document assistant.\n"
            "1. Answer the user query STRICTLY using the provided Context.\n"
            "2. Do NOT use outside knowledge. Do NOT guess.\n"
            "3. If the answer is not contained in the Context, output EXACTLY: "
            f"'{config.REFUSAL_RESPONSE}'\n"
            "4. Be concise and direct."
        )
    
    elif intent == QueryIntent.SUMMARY:
        return (
            "You are RAGex, a document summarization assistant.\n"
            "1. Summarize the key points from the provided Context.\n"
            "2. Focus on main ideas, themes, and important details.\n"
            "3. Structure your summary clearly with bullet points or paragraphs.\n"
            "4. Use ONLY information from the Context provided.\n"
            "5. Be comprehensive but concise."
        )
    
    elif intent == QueryIntent.DESCRIPTION:
        return (
            "You are RAGex, a document analysis assistant.\n"
            "1. Describe what the document(s) are about based on the Context.\n"
            "2. Identify the main topics, purpose, and scope.\n"
            "3. Mention the type of content (technical, educational, etc.).\n"
            "4. Use ONLY information from the Context provided.\n"
            "5. Be clear and informative."
        )
    
    # Fallback
    return (
        "You are RAGex, a helpful document assistant.\n"
        "Answer the user's question using the provided Context."
    )


def generate_answer(
    query: str,
    retrieved_chunks: List[Dict[str, Any]],
    intent: Optional[QueryIntent] = None,
    strict_refusal: bool = True,
) -> Dict[str, Any]:
    """
    Generate answer from retrieved chunks with intent-aware prompts.
    
    Args:
        query: User question
        retrieved_chunks: List of retrieved document chunks with metadata
        intent: Query intent (factual, summary, description)
        strict_refusal: Whether to refuse when no chunks (only for factual queries)
        
    Returns:
        Dict with 'answer' and 'sources' keys
    """
    intent = intent or QueryIntent.FACTUAL
    
    # Only refuse for factual queries with no chunks
    if not retrieved_chunks and strict_refusal:
        logger.info("Refusal triggered: No chunks provided.")
        return {
            "answer": config.REFUSAL_RESPONSE,
            "sources": []
        }
    
    # For summary/description, handle empty case gracefully
    if not retrieved_chunks:
        return {
            "answer": "No documents have been indexed yet. Please upload or index documents first.",
            "sources": []
        }

    context_text = _build_context(retrieved_chunks)
    sorted_sources = _collect_sources(retrieved_chunks)

    system_prompt = _system_prompt(intent)
    user_message = f"Context:\n{context_text}\n\nQuestion: {query}"

    try:
        orchestrator = get_orchestrator()
        final_answer = orchestrator.generate(system_prompt, user_message)

        # INVARIANT: Refusal response must be exact (INVARIANTS.md §5)
        # Normalize refusals only for factual intent
        if intent == QueryIntent.FACTUAL:
            if "not found in indexed documents" in final_answer.lower():
                # GUARD: Use exact configured refusal string, never paraphrase
                final_answer = config.REFUSAL_RESPONSE
                sorted_sources = []

        return {
            "answer": final_answer,
            "sources": sorted_sources
        }

    except ProviderUnavailable as e:
        logger.error(f"Provider unavailable: {e}")
        message = str(e).strip() or get_error_message("provider_unavailable")
        return {
            "answer": f"Error: {message}",
            "sources": []
        }
    except ProviderTimeout as e:
        logger.error(f"Provider timeout: {e}")
        message = get_error_message("provider_timeout")
        return {
            "answer": f"Error: {message}",
            "sources": []
        }
    except Exception as e:
        logger.error(f"Generation failed: {str(e)}", exc_info=True)
        return {
            "answer": "Error: Failed to generate response from LLM.",
            "sources": []
        }
