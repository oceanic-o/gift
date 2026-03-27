from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import User
from app.schemas.recommendation import (
    InteractionCreate, InteractionResponse,
    RecommendationWithGift, CompareResponse,
    MinimalRecommendation, GiftDetailsWithMetrics,
    ModelMetricResponse,
)
from app.services.recommendation_service import InteractionService, RecommendationService
from app.repositories.interaction_repository import ModelMetricRepository
from app.services.recommendation_service import _maybe_warmup_model_metrics

router = APIRouter(tags=["Recommendations & Interactions"])


@router.post("/interactions", response_model=InteractionResponse, status_code=201)
async def record_interaction(
    payload: InteractionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Record a user interaction (click, rating, purchase)."""
    service = InteractionService(db)
    interaction = await service.record_interaction(current_user.id, payload)
    return InteractionResponse.model_validate(interaction)


@router.get("/recommendations", response_model=list[RecommendationWithGift])
async def get_recommendations(
    top_n: int = Query(10, ge=1, le=50),
    occasion: str = Query(None),
    relationship: str = Query(None),
    min_price: float = Query(None, ge=0),
    max_price: float = Query(None, ge=0),
    age: str = Query(None, description="Recipient age group"),
    gender: str = Query(None, description="Recipient gender"),
    hobbies: str = Query(None, description="Recipient hobbies/interests"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get personalized hybrid gift recommendations for the logged-in user."""
    service = RecommendationService(db)
    return await service.get_personalized_recommendations(
        user_id=current_user.id,
        top_n=top_n,
        occasion=occasion,
        relationship=relationship,
        min_price=min_price,
        max_price=max_price,
        age=age,
        gender=gender,
        hobbies=hobbies,
    )


@router.get("/recommendations/minimal", response_model=list[MinimalRecommendation])
async def get_recommendations_minimal(
    top_n: int = Query(12, ge=1, le=50),
    occasion: str = Query(None),
    relationship: str = Query(None),
    min_price: float = Query(None, ge=0),
    max_price: float = Query(None, ge=0),
    age: str = Query(None),
    gender: str = Query(None),
    hobbies: str = Query(None, description="Selected hobby from dropdown"),
    age_exact: int = Query(None, description="Exact age of recipient (optional, derived from age group)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Image-only recommendations ideal for grid preview; right-click for details panel."""
    service = RecommendationService(db)
    return await service.get_minimal_recommendations(
        user_id=current_user.id,
        top_n=top_n,
        occasion=occasion,
        relationship=relationship,
        min_price=min_price,
        max_price=max_price,
        age=age,
        gender=gender,
        hobbies=hobbies,
    )


@router.get("/recommendations/{gift_id}/details", response_model=GiftDetailsWithMetrics)
async def get_recommendation_details(
    gift_id: int,
    occasion: str = Query(None),
    relationship: str = Query(None),
    min_price: float = Query(None, ge=0),
    max_price: float = Query(None, ge=0),
    age: str = Query(None),
    gender: str = Query(None),
    hobbies: str = Query(None),
    age_exact: int = Query(None, description="Exact age of recipient (optional)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Detailed metrics and full gift info for a selected recommendation (right-click panel)."""
    service = RecommendationService(db)
    return await service.get_gift_details_with_metrics(
        user_id=current_user.id,
        gift_id=gift_id,
        occasion=occasion,
        relationship=relationship,
        min_price=min_price,
        max_price=max_price,
        age=age,
        gender=gender,
        hobbies=hobbies,
    )


@router.get("/recommendations/compare", response_model=CompareResponse)
async def compare_models(
    top_n: int = Query(6, ge=1, le=20),
    occasion: str = Query(None),
    relationship: str = Query(None),
    min_price: float = Query(None, ge=0),
    max_price: float = Query(None, ge=0),
    query: str = Query(None, description="Natural language query for the RAG model"),
    age: str = Query(None, description="Recipient age group (e.g. 'Adult (26-40)')"),
    gender: str = Query(None, description="Recipient gender"),
    hobbies: str = Query(None, description="Recipient hobbies/interests"),
    age_exact: int = Query(None, description="Exact midpoint age of recipient (auto-derived from age group if omitted)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Run all 5 models (Content, Collaborative, Hybrid, Knowledge, RAG) and return their
    results and metrics side by side so the user can choose which model to use.
    """
    service = RecommendationService(db)
    return await service.compare_all_models(
        user_id=current_user.id,
        top_n=top_n,
        occasion=occasion,
        relationship=relationship,
        min_price=min_price,
        max_price=max_price,
        query=query,
        age=age,
        gender=gender,
        hobbies=hobbies,
        age_exact=age_exact,
    )


@router.get("/recommendations/metrics", response_model=list[ModelMetricResponse])
async def get_public_model_metrics(
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Public (logged-in user) view of model evaluation history.

    This intentionally exposes only aggregate metrics (precision/recall/F1/accuracy) and timestamps.
    """
    _ = current_user  # keep auth required, but not admin-only
    await _maybe_warmup_model_metrics(db)
    repo = ModelMetricRepository(db)
    metrics = await repo.get_all_metrics()
    metrics = list(metrics or [])
    metrics.sort(key=lambda m: m.evaluated_at, reverse=True)
    metrics = metrics[:limit]
    return [ModelMetricResponse.model_validate(m) for m in metrics]
