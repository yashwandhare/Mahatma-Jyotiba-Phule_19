import logging
from typing import List, Dict, Any
from openai import OpenAI
from backend.app.core import config

logger = logging.getLogger(__name__)

# Initialize OpenAI client for Groq
if config.GROQ_API_KEY:
    client = OpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=config.GROQ_API_KEY
    )
else:
    client = None
    logger.error("GROQ_API_KEY not configured. Generation will fail.")

def generate_answer(query: str, retrieved_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate grounded answer or refuse if context is empty."""
    if not retrieved_chunks:
        logger.info("Refusal triggered: No chunks provided.")
        return {
            "answer": config.REFUSAL_RESPONSE,
            "sources": []
        }

    if not client:
        logger.error("Generation attempted without API client.")
        return {
            "answer": "Error: Groq API key not configured.",
            "sources": []
        }

    # 2. Prepare Context
    context_text = ""
    for i, chunk in enumerate(retrieved_chunks):
        text = chunk.get("text", "").strip()
        context_text += f"--- CHUNK {i+1} ---\n{text}\n\n"

    # Extract sources without LLM hallucination
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
    
    sorted_sources = sorted(list(unique_sources))

    system_prompt = (
        "You are RAGex, a precise document assistant.\n"
        "1. Answer the user query STRICTLY using the provided Context.\n"
        "2. Do NOT use outside knowledge. Do NOT guess.\n"
        "3. If the answer is not contained in the Context, output EXACTLY: "
        f"'{config.REFUSAL_RESPONSE}'\n"
        "4. Be concise and direct."
    )

    user_message = (
        f"Context:\n{context_text}\n\n"
        f"Question: {query}"
    )

    try:
        logger.info(f"Generating answer with model {config.GROQ_MODEL}...")
        response = client.chat.completions.create(
            model=config.GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=config.GENERATION_TEMPERATURE,
            max_tokens=config.GENERATION_MAX_TOKENS
        )
        
        final_answer = response.choices[0].message.content.strip()

        # Enforce exact refusal format
        if "not found in indexed documents" in final_answer.lower():
            final_answer = config.REFUSAL_RESPONSE
            sorted_sources = []

        return {
            "answer": final_answer,
            "sources": sorted_sources
        }

    except Exception as e:
        logger.error(f"Generation failed: {str(e)}")
        return {
            "answer": "Error: Failed to generate response from LLM.",
            "sources": []
        }