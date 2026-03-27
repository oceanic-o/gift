from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_admin
from app.schemas.recommendation import (
    AdminStats,
    ModelMetricResponse,
    DatasetMetadataResponse,
    DatabaseSchemaResponse,
    AdminQueryRequest,
    AdminQueryResponse,
    EnvSettingsResponse,
    EnvSettingsUpdate,
)
from app.schemas.user import UserResponse, UserRoleUpdate
from app.schemas.recommendation import InteractionResponse
from app.services.admin_service import AdminService

router = APIRouter(prefix="/admin", tags=["Admin Dashboard"])


@router.get("/stats", response_model=AdminStats)
async def get_stats(
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    """Get system-wide statistics."""
    service = AdminService(db)
    return await service.get_stats()


@router.get("/metrics", response_model=list[ModelMetricResponse])
async def get_metrics(
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    """Get all model evaluation metrics history."""
    service = AdminService(db)
    metrics = await service.get_all_metrics()
    return [ModelMetricResponse.model_validate(m) for m in metrics]


@router.get("/users", response_model=list[UserResponse])
async def get_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    """List all registered users."""
    service = AdminService(db)
    users = await service.get_all_users(skip=skip, limit=limit)
    return [UserResponse.model_validate(u) for u in users]


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    """Delete a user account and related data (admin only)."""
    service = AdminService(db)
    return await service.delete_user(user_id)


@router.patch("/users/{user_id}/role", response_model=UserResponse)
async def update_user_role(
    user_id: int,
    payload: UserRoleUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    """Update a user's role (admin only)."""
    service = AdminService(db)
    user = await service.update_user_role(user_id, payload.role)
    return UserResponse.model_validate(user)


@router.get("/interactions", response_model=list[InteractionResponse])
async def get_interactions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    """List all user interactions (paginated)."""
    service = AdminService(db)
    interactions = await service.get_all_interactions(skip=skip, limit=limit)
    return [InteractionResponse.model_validate(i) for i in interactions]


@router.delete("/interactions/{interaction_id}")
async def delete_interaction(
    interaction_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    """Delete an interaction record (admin only)."""
    service = AdminService(db)
    return await service.delete_interaction(interaction_id)


@router.post("/gifts/import")
async def import_gifts(
    limit: int | None = Query(None, ge=1, le=5000),
    force: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    """Import gifts from ../data/gifts_50k.json (admin only)."""
    service = AdminService(db)
    return await service.import_gifts_from_json(
    json_path="../data/gifts_50k.json",
        limit=limit,
        force=force,
    )


@router.post("/catalog/reset")
async def reset_catalog(
    limit: int | None = Query(None, ge=1, le=5000),
    embed_batch_size: int = Query(100, ge=10, le=200),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    """Delete all existing gift data and reload from ../data/gifts_50k.json, then embed + retrain."""
    service = AdminService(db)
    return await service.reset_and_populate_catalog(
    json_path="../data/gifts_50k.json",
        limit=limit,
        embed_batch_size=embed_batch_size,
    )


@router.get("/dataset/metadata", response_model=DatasetMetadataResponse)
async def get_dataset_metadata(
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    """Return metadata about the gifts_50k.json dataset used for imports."""
    service = AdminService(db)
    return await service.get_dataset_metadata()


@router.get("/db/schema", response_model=DatabaseSchemaResponse)
async def get_database_schema(
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    """Return database table/column schema for admin display."""
    service = AdminService(db)
    return await service.get_database_schema()


@router.post("/db/query", response_model=AdminQueryResponse)
async def run_admin_query(
    payload: AdminQueryRequest,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    """Run a read-only SQL query for admin debugging."""
    service = AdminService(db)
    return await service.run_readonly_query(payload.sql, payload.max_rows)


@router.post("/embeddings")
async def embed_gifts(
    batch_size: int = Query(50, ge=10, le=200),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    """Generate embeddings for gifts without vectors (admin only)."""
    service = AdminService(db)
    return await service.embed_gifts(batch_size=batch_size)


@router.post("/web-gifts/ingest")
async def ingest_web_gifts(
    query: str = Query(..., min_length=3),
    limit: int | None = Query(None, ge=1, le=100),
    occasion: str | None = Query(None),
    relationship: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    """Fetch gifts from the web and store them in the web_gifts table (admin only)."""
    service = AdminService(db)
    return await service.ingest_web_gifts(
        query=query,
        limit=limit,
        occasion=occasion,
        relationship=relationship,
    )


@router.post("/retrain")
async def retrain_model(
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    """Retrain the recommendation model with latest interaction data."""
    service = AdminService(db)
    return await service.retrain_model()


@router.post("/evaluate")
async def evaluate_model(
    cross_validate: bool = Query(False, description="Enable 5-fold cross-validation"),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    """
    Evaluate the hybrid recommendation model.
    Runs 80/20 train-test split evaluation.
    Optionally runs 5-fold cross-validation.
    Stores results to model_metrics table.
    """
    service = AdminService(db)
    return await service.evaluate_model(cross_validate=cross_validate)


@router.post("/tune")
async def tune_models(
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    """Grid-search tuning for content/collab and tfidf/embed weights; returns metrics for graphs."""
    service = AdminService(db)
    return await service.tune_and_evaluate()


@router.get("/settings", response_model=EnvSettingsResponse)
async def get_settings(
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    """Get backend and frontend .env settings (admin only)."""
    service = AdminService(db)
    return await service.get_env_settings()


@router.patch("/settings")
async def update_settings(
    payload: EnvSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    """Update backend and/or frontend .env settings (admin only)."""
    service = AdminService(db)
    return await service.update_env_settings(payload)
