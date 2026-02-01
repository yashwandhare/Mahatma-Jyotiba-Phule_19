from backend.app.core import logger
from backend.app.core.validation import check_startup, get_health_status, ConfigValidationError
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from backend.app.api.routes import router
import logging
import sys

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

# Run startup checks
try:
    check_startup()
except ConfigValidationError as e:
    log.error(f"Startup validation failed: {e}")
    log.error("Application cannot start with invalid configuration")
    sys.exit(1)

app.include_router(router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    log.warning(f"Request validation error: {exc}")
    return JSONResponse(
        status_code=422,
        content={
            "answer": "Error: Invalid request payload.",
            "sources": []
        }
    )

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
    """Detailed health check with provider validation."""
    return get_health_status()