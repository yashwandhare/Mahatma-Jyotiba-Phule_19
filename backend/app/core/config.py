"""
Configuration management with strict load order and explicit defaults.

Load Order (strict precedence):
1. Hard-coded defaults (defined in Field() defaults)
2. .env file (if present in project root)
3. Environment variables (override .env values)
4. CLI flags (via environment variables set in ragcli.py)

Every configuration value has an explicit default. Missing critical configuration
(like GROQ_API_KEY when using Groq provider) produces runtime validation errors.
Non-critical missing values log a single warning at startup.
"""

import logging
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

_BACKEND_DIR = Path(__file__).resolve().parents[2]
_PROJECT_ROOT = _BACKEND_DIR.parent
_DEFAULT_VECTOR_DB_PATH = str(_BACKEND_DIR / "data" / "vectordb")

# Track whether we've logged config warnings to avoid spam
_warnings_logged = False


class Settings(BaseSettings):
    """
    RAGex configuration with explicit defaults and validation.
    
    All values have defaults. Critical values (API keys for active providers)
    are validated at first use, not at startup, to allow config inspection
    without requiring valid secrets.
    """
    model_config = SettingsConfigDict(
        env_file=str(_PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Provider Configuration (Critical)
    RAG_PROVIDER: str = Field(
        default="groq",
        description="LLM provider: 'groq' or 'ollama'",
        validation_alias=AliasChoices("RAG_PROVIDER", "RAG_MODEL_PROVIDER")
    )
    RAG_MODEL_NAME: str = Field(
        default="llama-3.3-70b-versatile",
        description="Model name for the active provider",
        validation_alias=AliasChoices("RAG_MODEL_NAME", "GROQ_MODEL")
    )

    # Provider-specific Configuration (Critical for active provider)
    GROQ_API_KEY: Optional[str] = Field(
        default=None,
        description="Groq API key (required when RAG_PROVIDER=groq)",
        validation_alias="GROQ_API_KEY"
    )
    OLLAMA_BASE_URL: str = Field(
        default="http://localhost:11434",
        description="Ollama server URL (used when RAG_PROVIDER=ollama)",
        validation_alias="OLLAMA_BASE_URL"
    )
    OFFLINE_MODE: bool = Field(
        default=False,
        description="Disable all remote network calls (Ollama localhost only)",
        validation_alias=AliasChoices("RAG_OFFLINE", "OFFLINE_MODE")
    )
    LLM_TIMEOUT: int = Field(
        default=45,
        ge=1,
        le=300,
        description="LLM request timeout in seconds",
        validation_alias="LLM_TIMEOUT"
    )

    # Embeddings / Storage (Non-critical, warnings only)
    EMBEDDING_MODEL_NAME: str = Field(
        default="all-MiniLM-L6-v2",
        description="Sentence-transformers embedding model",
        validation_alias=AliasChoices("EMBEDDING_MODEL_NAME", "EMBEDDING_MODEL")
    )
    VECTOR_DB_PATH: str = Field(
        default=_DEFAULT_VECTOR_DB_PATH,
        description="Path to ChromaDB persistent storage",
        validation_alias=AliasChoices("VECTOR_DB_PATH", "DB_PATH")
    )
    COLLECTION_NAME: str = Field(
        default="ragex_chunks",
        description="ChromaDB collection name",
        validation_alias="COLLECTION_NAME"
    )

    # Retrieval Configuration (Non-critical)
    CANDIDATE_K: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Initial candidate pool size for retrieval",
        validation_alias="CANDIDATE_K"
    )
    MIN_SCORE_THRESHOLD: float = Field(
        default=0.40,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score threshold",
        validation_alias="MIN_SCORE_THRESHOLD"
    )
    DROP_OFF_THRESHOLD: float = Field(
        default=0.10,
        ge=0.0,
        le=1.0,
        description="Drop-off threshold for relevance filtering",
        validation_alias="DROP_OFF_THRESHOLD"
    )

    # Generation Configuration (Non-critical)
    REFUSAL_RESPONSE: str = Field(
        default="Answer: Not found in indexed documents.",
        description="Response when answer is not found",
        validation_alias="REFUSAL_RESPONSE"
    )
    GENERATION_TEMPERATURE: float = Field(
        default=0.1,
        ge=0.0,
        le=2.0,
        description="LLM sampling temperature",
        validation_alias="GENERATION_TEMPERATURE"
    )
    GENERATION_MAX_TOKENS: int = Field(
        default=500,
        ge=1,
        le=4096,
        description="Maximum tokens in LLM response",
        validation_alias="GENERATION_MAX_TOKENS"
    )

    @field_validator("RAG_PROVIDER")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        """Normalize and validate provider name."""
        provider = v.strip().lower()
        if provider not in {"groq", "ollama"}:
            raise ValueError("RAG_PROVIDER must be 'groq' or 'ollama'.")
        return provider

    @field_validator("OLLAMA_BASE_URL")
    @classmethod
    def normalize_ollama_url(cls, v: str) -> str:
        """Strip trailing slash from Ollama URL."""
        return v.rstrip("/")

    @model_validator(mode="after")
    def log_config_warnings(self) -> "Settings":
        """Log warnings for non-critical missing config (once per process)."""
        global _warnings_logged
        if _warnings_logged:
            return self
        
        _warnings_logged = True
        
        # Check if .env exists
        env_file = _PROJECT_ROOT / ".env"
        if not env_file.exists():
            logger.warning(
                f"No .env file found at {env_file}. "
                "Using defaults. Run 'ragex config' to see effective values."
            )
        
        return self

    def validate_runtime_requirements(self) -> None:
        """
        Validate critical configuration requirements at runtime.
        
        Called by orchestrator/CLI before making actual LLM calls.
        Raises ValueError with clear message if critical config is missing.
        """
        # Only validate API key for Groq when it's the active provider
        if self.RAG_PROVIDER == "groq":
            if not self.GROQ_API_KEY or not self.GROQ_API_KEY.strip():
                raise ValueError(
                    "GROQ_API_KEY is required when RAG_PROVIDER=groq. "
                    "Set it in .env or export GROQ_API_KEY=your-key"
                )
        
        # Validate offline mode constraints
        if self.OFFLINE_MODE and self.RAG_PROVIDER != "ollama":
            raise ValueError(
                "OFFLINE_MODE=1 requires RAG_PROVIDER=ollama. "
                "Cannot use remote providers in offline mode."
            )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Get singleton settings instance.
    
    Loads configuration in strict order:
    1. Defaults (Field defaults)
    2. .env file (project root)
    3. Environment variables (override .env)
    
    This function is cached - config is loaded once per process.
    """
    return Settings()


def get_config_dict(mask_secrets: bool = True) -> dict:
    """
    Get all configuration values as a dictionary.
    
    Args:
        mask_secrets: If True, masks API keys to show only first/last 4 chars
        
    Returns:
        Dictionary of config key-value pairs
    """
    settings = get_settings()
    config_dict = {}
    
    # Get all fields with descriptions
    for field_name, field_info in settings.model_fields.items():
        value = getattr(settings, field_name)
        
        # Mask secrets (API keys)
        if mask_secrets and field_name.endswith("_KEY") and value:
            if len(value) > 8:
                value = f"{value[:4]}...{value[-4:]}"
            else:
                value = "***"
        
        # Convert Path objects to strings
        if hasattr(value, "__str__"):
            value = str(value)
        
        config_dict[field_name] = {
            "value": value,
            "description": field_info.description or "",
            "default": field_info.default if field_info.default is not None else "None"
        }
    
    return config_dict


settings = get_settings()

# Backwards-compatible module-level exports
RAG_PROVIDER = settings.RAG_PROVIDER
RAG_MODEL_NAME = settings.RAG_MODEL_NAME
GROQ_API_KEY = settings.GROQ_API_KEY
OLLAMA_BASE_URL = settings.OLLAMA_BASE_URL
OFFLINE_MODE = settings.OFFLINE_MODE
LLM_TIMEOUT = settings.LLM_TIMEOUT

EMBEDDING_MODEL = settings.EMBEDDING_MODEL_NAME
DB_PATH = settings.VECTOR_DB_PATH
COLLECTION_NAME = settings.COLLECTION_NAME

CANDIDATE_K = settings.CANDIDATE_K
MIN_SCORE_THRESHOLD = settings.MIN_SCORE_THRESHOLD
DROP_OFF_THRESHOLD = settings.DROP_OFF_THRESHOLD

REFUSAL_RESPONSE = settings.REFUSAL_RESPONSE
GENERATION_TEMPERATURE = settings.GENERATION_TEMPERATURE
GENERATION_MAX_TOKENS = settings.GENERATION_MAX_TOKENS
