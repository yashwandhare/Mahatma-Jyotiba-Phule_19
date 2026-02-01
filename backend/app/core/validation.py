"""Configuration validation and startup checks."""

import logging
import os
import urllib.request
from typing import List, Tuple, Optional
from pathlib import Path

from backend.app.core import config

logger = logging.getLogger(__name__)


class ConfigValidationError(Exception):
    """Configuration is invalid."""
    pass


def validate_config() -> List[Tuple[str, str, str]]:
    """
    Validate configuration and return warnings/errors.
    
    Returns:
        List of (level, component, message) tuples
        level: 'info', 'warning', or 'error'
    """
    issues = []
    
    # Provider validation
    if config.RAG_PROVIDER not in ('groq', 'ollama'):
        issues.append(('error', 'provider', f"Invalid provider: {config.RAG_PROVIDER}"))
    
    # Groq-specific checks
    if config.RAG_PROVIDER == 'groq':
        if not config.GROQ_API_KEY:
            if not config.OFFLINE_MODE:
                issues.append(('error', 'groq', "GROQ_API_KEY not set (required for groq provider)"))
        else:
            issues.append(('info', 'groq', f"API key configured (length: {len(config.GROQ_API_KEY)})"))
        
        if config.OFFLINE_MODE:
            issues.append(('warning', 'groq', "Offline mode enabled; Groq will be unavailable"))
    
    # Ollama-specific checks
    if config.RAG_PROVIDER == 'ollama':
        try:
            url = f"{config.OLLAMA_BASE_URL}/api/tags"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=2) as response:
                if response.status == 200:
                    issues.append(('info', 'ollama', f"Ollama is reachable at {config.OLLAMA_BASE_URL}"))
                else:
                    issues.append(('warning', 'ollama', f"Ollama returned status {response.status}"))
        except Exception as e:
            issues.append(('error', 'ollama', f"Ollama unreachable at {config.OLLAMA_BASE_URL}: {e}"))
    
    # Model validation
    if not config.RAG_MODEL_NAME:
        issues.append(('error', 'model', "RAG_MODEL_NAME not set"))
    else:
        issues.append(('info', 'model', f"Model: {config.RAG_MODEL_NAME}"))
    
    # Embedding model
    issues.append(('info', 'embedding', f"Embedding model: {config.EMBEDDING_MODEL}"))
    
    # Vector DB path
    db_path = Path(config.DB_PATH)
    if db_path.exists():
        if not os.access(config.DB_PATH, os.W_OK):
            issues.append(('error', 'vectordb', f"No write access to {config.DB_PATH}"))
        else:
            issues.append(('info', 'vectordb', f"Vector DB: {config.DB_PATH}"))
    else:
        # Try to create
        try:
            db_path.mkdir(parents=True, exist_ok=True)
            issues.append(('info', 'vectordb', f"Created vector DB directory: {config.DB_PATH}"))
        except Exception as e:
            issues.append(('error', 'vectordb', f"Cannot create {config.DB_PATH}: {e}"))
    
    # Timeout validation
    if config.LLM_TIMEOUT <= 0:
        issues.append(('warning', 'timeout', f"Invalid timeout: {config.LLM_TIMEOUT}, using 45s"))
    
    return issues


def check_startup() -> None:
    """
    Run startup checks and log results.
    Raises ConfigValidationError if critical issues found.
    """
    logger.info("Running startup configuration checks...")
    
    issues = validate_config()
    
    errors = []
    for level, component, message in issues:
        if level == 'error':
            logger.error(f"[{component}] {message}")
            errors.append(message)
        elif level == 'warning':
            logger.warning(f"[{component}] {message}")
        else:
            logger.info(f"[{component}] {message}")
    
    if errors:
        raise ConfigValidationError(
            f"Configuration validation failed with {len(errors)} error(s). "
            "Check logs for details."
        )
    
    logger.info("✓ Configuration validation passed")


def get_health_status() -> dict:
    """Get detailed health status for /health endpoint."""
    from backend.app.rag import store
    
    try:
        collection = store.get_collection()
        collection_size = collection.count()
    except Exception as e:
        logger.error(f"Failed to get collection size: {e}")
        collection_size = -1
    
    # Check provider availability
    provider_available = False
    provider_error = None
    
    if config.RAG_PROVIDER == 'groq':
        provider_available = bool(config.GROQ_API_KEY) and not config.OFFLINE_MODE
        if not provider_available:
            if config.OFFLINE_MODE:
                provider_error = "offline_mode"
            elif not config.GROQ_API_KEY:
                provider_error = "no_api_key"
    
    elif config.RAG_PROVIDER == 'ollama':
        try:
            url = f"{config.OLLAMA_BASE_URL}/api/tags"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=2) as response:
                provider_available = response.status == 200
        except Exception as e:
            provider_available = False
            provider_error = str(e)
    
    return {
        "status": "healthy",
        "provider": config.RAG_PROVIDER,
        "model": config.RAG_MODEL_NAME,
        "embedding_model": config.EMBEDDING_MODEL,
        "vector_db_path": config.DB_PATH,
        "collection_size": collection_size,
        "offline_mode": config.OFFLINE_MODE,
        "provider_available": provider_available,
        "provider_error": provider_error if not provider_available else None,
    }
