import logging
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

_BACKEND_DIR = Path(__file__).resolve().parents[2]
_DEFAULT_VECTOR_DB_PATH = str(_BACKEND_DIR / "data" / "vectordb")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    # Provider Configuration
    RAG_PROVIDER: str = Field(default="groq", validation_alias=AliasChoices("RAG_PROVIDER", "RAG_MODEL_PROVIDER"))
    RAG_MODEL_NAME: str = Field(default="llama-3.3-70b-versatile", validation_alias=AliasChoices("RAG_MODEL_NAME", "GROQ_MODEL"))

    # Provider-specific Configuration
    GROQ_API_KEY: Optional[str] = Field(default=None, validation_alias="GROQ_API_KEY")
    OLLAMA_BASE_URL: str = Field(default="http://localhost:11434", validation_alias="OLLAMA_BASE_URL")
    OFFLINE_MODE: bool = Field(default=False, validation_alias=AliasChoices("RAG_OFFLINE", "OFFLINE_MODE"))
    LLM_TIMEOUT: int = Field(default=45, validation_alias="LLM_TIMEOUT")  # seconds

    # Embeddings / Storage
    EMBEDDING_MODEL_NAME: str = Field(default="all-MiniLM-L6-v2", validation_alias=AliasChoices("EMBEDDING_MODEL_NAME", "EMBEDDING_MODEL"))
    VECTOR_DB_PATH: str = Field(default=_DEFAULT_VECTOR_DB_PATH, validation_alias=AliasChoices("VECTOR_DB_PATH", "DB_PATH"))
    COLLECTION_NAME: str = Field(default="ragex_chunks", validation_alias="COLLECTION_NAME")

    # Retrieval Configuration
    CANDIDATE_K: int = Field(default=20, validation_alias="CANDIDATE_K")
    MIN_SCORE_THRESHOLD: float = Field(default=0.40, validation_alias="MIN_SCORE_THRESHOLD")
    DROP_OFF_THRESHOLD: float = Field(default=0.10, validation_alias="DROP_OFF_THRESHOLD")

    # Generation Configuration
    REFUSAL_RESPONSE: str = Field(default="Answer: Not found in indexed documents.", validation_alias="REFUSAL_RESPONSE")
    GENERATION_TEMPERATURE: float = Field(default=0.1, validation_alias="GENERATION_TEMPERATURE")
    GENERATION_MAX_TOKENS: int = Field(default=500, validation_alias="GENERATION_MAX_TOKENS")

    @field_validator("RAG_PROVIDER")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        provider = v.strip().lower()
        if provider not in {"groq", "ollama"}:
            raise ValueError("RAG_PROVIDER must be 'groq' or 'ollama'.")
        return provider

    @field_validator("OLLAMA_BASE_URL")
    @classmethod
    def normalize_ollama_url(cls, v: str) -> str:
        return v.rstrip("/")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


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
