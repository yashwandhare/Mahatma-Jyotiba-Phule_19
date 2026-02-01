"""Shared user-facing error messages and helpers."""

from __future__ import annotations

from typing import Dict

_ERROR_MESSAGES: Dict[str, str] = {
    "offline_mode": (
        "Offline mode is enabled. Remote providers are disabled. Use a local Ollama model or disable offline mode."
    ),
    "offline_local_ollama": (
        "Offline mode requires Ollama to run on localhost. Update OLLAMA_BASE_URL or disable offline mode."
    ),
    "provider_unavailable": (
        "LLM provider unavailable. Please try again later or switch providers."
    ),
    "provider_timeout": (
        "LLM provider timed out. Please try again in a moment."
    ),
    "no_valid_documents": (
        "No valid documents were found. Provide supported files and try again."
    ),
    "upload_empty": (
        "Uploaded files are empty or unsupported. Provide supported documents and retry."
    ),
    "backend_init_failed": (
        "Failed to initialize the RAGex backend. Run with --verbose for details."
    ),
    "index_clean_failed": (
        "Failed to clear the index. Run with --verbose for details."
    ),
    "indexing_failed": (
        "Indexing failed unexpectedly. Run with --verbose for details."
    ),
    "documents_list_failed": (
        "Unable to retrieve document metadata at this time."
    ),
    "vector_store_unavailable": (
        "Vector store is unavailable or unreadable. Run 'ragex clean' to rebuild the index."
    ),
    "generic": (
        "Something went wrong. Please try again or contact the maintainer."
    ),
}


def get_error_message(code: str, fallback: str | None = None) -> str:
    """Return the canonical error message for a given code."""
    if code in _ERROR_MESSAGES:
        return _ERROR_MESSAGES[code]
    if fallback:
        return fallback
    return _ERROR_MESSAGES["generic"]
