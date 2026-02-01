from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, validator
from typing import List
import logging

from backend.app.rag import retriever, generator

logger = logging.getLogger(__name__)
router = APIRouter()

class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)
    
    @validator('question')
    def question_not_empty(cls, v):
        if not v.strip():
            raise ValueError('Question cannot be empty or whitespace only')
        return v.strip()

class AskResponse(BaseModel):
    answer: str
    sources: List[str]

@router.post("/ask", response_model=AskResponse, status_code=status.HTTP_200_OK)
async def ask_question(request: AskRequest):
    """
    Answer question from indexed documents.
    Returns grounded answer with sources or refusal if information not found.
    """
    try:
        retrieval_result = retriever.retrieve(request.question)
        chunks = retrieval_result.get("chunks", [])
        
        generation_result = generator.generate_answer(request.question, chunks)
        
        return AskResponse(
            answer=generation_result["answer"],
            sources=generation_result["sources"]
        )
        
    except ValueError as e:
        logger.warning(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Internal error during /ask: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred while processing your request."
        )