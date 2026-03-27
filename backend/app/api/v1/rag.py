from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import User
from app.schemas.recommendation import RAGQueryCreate, RAGQueryResponse
from app.services.rag.rag_service import RAGService

router = APIRouter(prefix="/rag", tags=["RAG – Gift Advisor"])


@router.post("/ask")
async def ask_rag(
    payload: RAGQueryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Ask the AI Gift Advisor a natural language question.
    Uses Retrieval-Augmented Generation (RAG) with pgvector + OpenAI.

    Example queries:
    - "What's a good gift for my mom's 60th birthday under $100?"
    - "I need a wedding gift for my colleague who loves cooking"
    """
    service = RAGService()
    result = await service.ask(db, current_user.id, payload)
    return result


@router.post("/embed-gifts", status_code=200)
async def embed_all_gifts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Trigger embedding generation for all gifts without embeddings.
    (Admin use – also accessible to authenticated users for demo purposes)
    """
    service = RAGService()
    return await service.embed_and_store_gifts(db)
