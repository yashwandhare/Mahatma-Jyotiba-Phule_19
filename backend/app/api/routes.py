import logging
import shutil
import tempfile
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, File, UploadFile, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator

from backend.app.rag import retriever, generator, loader, chunker, store
from backend.app.rag.intent import detect_intent, get_retrieval_strategy, QueryIntent

logger = logging.getLogger(__name__)
router = APIRouter()

class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)
    intent: Optional[str] = None  # Optional explicit intent: factual, summary, description
    
    @validator('question')
    def question_not_empty(cls, v):
        if not v.strip():
            raise ValueError('Question cannot be empty or whitespace only')
        return v.strip()

class AskResponse(BaseModel):
    answer: str
    sources: List[str]
    intent: str  # Detected or explicit intent


class IndexRequest(BaseModel):
    paths: List[str] = Field(..., min_items=1)
    clear_index: bool = False


class IndexResponse(BaseModel):
    status: str
    message: str
    segments_indexed: int
    chunks_indexed: int
    collection_count: int


class DocumentInfo(BaseModel):
    filename: str
    chunk_count: int


class DocumentsResponse(BaseModel):
    total_chunks: int
    total_documents: int
    documents: List[DocumentInfo]


@router.get("/documents", response_model=DocumentsResponse, status_code=status.HTTP_200_OK)
async def list_documents():
    """List all indexed documents with metadata."""
    try:
        collection = store.get_collection()
        total_chunks = collection.count()
        
        if total_chunks == 0:
            return DocumentsResponse(
                total_chunks=0,
                total_documents=0,
                documents=[]
            )
        
        # Get all metadatas to count chunks per file
        result = collection.get(include=["metadatas"])
        metadatas = result.get("metadatas", [])
        
        # Count chunks per filename
        file_counts = {}
        for meta in metadatas:
            if meta:
                filename = meta.get("filename", "unknown")
                file_counts[filename] = file_counts.get(filename, 0) + 1
        
        # Build document list sorted by chunk count
        documents = [
            DocumentInfo(filename=fname, chunk_count=count)
            for fname, count in sorted(file_counts.items(), key=lambda x: (-x[1], x[0]))
        ]
        
        return DocumentsResponse(
            total_chunks=total_chunks,
            total_documents=len(documents),
            documents=documents
        )
        
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "total_chunks": 0,
                "total_documents": 0,
                "documents": [],
                "error": "Failed to retrieve document list"
            }
        )


@router.post("/ask", response_model=AskResponse, status_code=status.HTTP_200_OK)
async def ask_question(request: AskRequest):
    """
    Answer question from indexed documents with intent-aware retrieval.
    Supports factual, summary, and description query types.
    """
    try:
        # Detect intent or use explicit intent
        if request.intent:
            try:
                query_intent = QueryIntent(request.intent.lower())
            except ValueError:
                query_intent = detect_intent(request.question)
        else:
            query_intent = detect_intent(request.question)
        
        # Get retrieval strategy for this intent
        strategy = get_retrieval_strategy(query_intent)
        
        # Retrieve with intent-specific parameters
        retrieval_result = retriever.retrieve(
            request.question,
            top_k=strategy["top_k"],
            min_similarity=strategy["min_similarity"],
            diverse_sampling=strategy["diverse_sampling"]
        )
        chunks = retrieval_result.get("chunks", [])
        
        # Generate with intent-aware prompts
        generation_result = generator.generate_answer(
            request.question,
            chunks,
            intent=query_intent,
            strict_refusal=strategy["strict_refusal"]
        )
        
        return AskResponse(
            answer=generation_result["answer"],
            sources=generation_result["sources"],
            intent=query_intent.value
        )
        
    except ValueError as e:
        logger.warning(f"Validation error: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "answer": f"Error: {str(e)}",
                "sources": [],
                "intent": "error"
            }
        )
    except Exception as e:
        logger.error(f"Internal error during /ask: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "answer": "Error: An internal error occurred while processing your request.",
                "sources": [],
                "intent": "error"
            }
        )


def _index_documents(docs: List[dict], clear_index: bool) -> IndexResponse:
    if clear_index:
        store.clear_index()

    collection = store.get_collection()
    before = collection.count()

    chunker_inst = chunker.Chunker()
    chunks = chunker_inst.chunk(docs)
    store.index_chunks(chunks)

    after = collection.count()

    return IndexResponse(
        status="ok",
        message="Indexing complete",
        segments_indexed=len(docs),
        chunks_indexed=len(chunks),
        collection_count=after,
    )


@router.post("/index", response_model=IndexResponse, status_code=status.HTTP_200_OK)
async def index_paths(payload: IndexRequest):
    try:
        docs = loader.load_inputs(payload.paths)
        if not docs:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status": "error",
                    "message": "No valid documents found for provided paths.",
                    "segments_indexed": 0,
                    "chunks_indexed": 0,
                    "collection_count": store.get_collection().count(),
                },
            )

        return _index_documents(docs, payload.clear_index)

    except Exception as e:
        logger.error(f"Internal error during /index: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "message": "Failed to index documents.",
                "segments_indexed": 0,
                "chunks_indexed": 0,
                "collection_count": store.get_collection().count(),
            },
        )


@router.post("/upload", response_model=IndexResponse, status_code=status.HTTP_200_OK)
async def upload_files(files: List[UploadFile] = File(...), clear_index: bool = False):
    if not files:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "status": "error",
                "message": "No files uploaded.",
                "segments_indexed": 0,
                "chunks_indexed": 0,
                "collection_count": store.get_collection().count(),
            },
        )

    tmp_dir = Path(tempfile.mkdtemp(prefix="ragex_upload_"))
    saved_paths = []

    try:
        for file in files:
            safe_name = Path(file.filename or "upload").name
            dest = tmp_dir / safe_name
            with dest.open("wb") as f:
                shutil.copyfileobj(file.file, f)
            saved_paths.append(str(dest))

        docs = loader.load_inputs(saved_paths)
        if not docs:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status": "error",
                    "message": "Uploaded files are empty or unsupported.",
                    "segments_indexed": 0,
                    "chunks_indexed": 0,
                    "collection_count": store.get_collection().count(),
                },
            )

        return _index_documents(docs, clear_index)

    except Exception as e:
        logger.error(f"Internal error during /upload: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "message": "Failed to process uploaded files.",
                "segments_indexed": 0,
                "chunks_indexed": 0,
                "collection_count": store.get_collection().count(),
            },
        )
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)