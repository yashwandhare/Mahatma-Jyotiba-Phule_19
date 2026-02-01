from dotenv import load_dotenv
load_dotenv()

from backend.app.core import logger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.api.routes import router
import logging

log = logging.getLogger(__name__)

app = FastAPI(
    title="RAGex API",
    description="Context-Aware Document QA with Dynamic RAG",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "RAGex",
        "message": "Context-Aware Document QA API"
    }

@app.get("/health")
async def health():
    """Detailed health check."""
    from backend.app.core import config
    return {
        "status": "healthy",
        "groq_configured": bool(config.GROQ_API_KEY),
        "embedding_model": config.EMBEDDING_MODEL,
        "generation_model": config.GROQ_MODEL
    }