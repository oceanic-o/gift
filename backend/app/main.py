"""
Gift Recommendation System – Main Application Entry Point.

Production-ready FastAPI application with:
- Async PostgreSQL + pgvector
- JWT Authentication
- Hybrid Recommendation Engine (Content-Based + Collaborative Filtering)
- RAG Gift Advisor (OpenAI + pgvector)
- Admin Dashboard
- Structured Logging
- CORS support
- Health check endpoint
"""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.core.config import settings
from app.core.database import engine, Base
from app.core.logging import setup_logging, logger
from app.api.v1 import api_router
from app.services.recommendation.hybrid import get_recommender
from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.repositories.user_repository import UserRepository
from app.models.models import User, UserRole
from app.services.evaluation.evaluator import RecommendationEvaluator
from app.repositories.gift_repository import GiftRepository


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle: startup and shutdown events."""
    setup_logging(debug=settings.DEBUG)
    logger.info("app.starting", version=settings.APP_VERSION)

    # Ensure admin user exists based on env configuration
    try:
        async with AsyncSessionLocal() as db:
            if settings.ADMIN_EMAIL and settings.ADMIN_PASSWORD:
                repo = UserRepository(db)
                admin_email = settings.ADMIN_EMAIL.lower()
                admin_user = await repo.get_by_email(admin_email)
                if admin_user is None:
                    admin_user = User(
                        name="System Admin",
                        email=admin_email,
                        password_hash=hash_password(settings.ADMIN_PASSWORD),
                        role=UserRole.admin,
                        provider="local",
                    )
                    db.add(admin_user)
                    await db.commit()
                    await db.refresh(admin_user)
                    logger.info("admin.seeded", email=admin_email)
                elif admin_user.provider == "local":
                    updated = False
                    if admin_user.role != UserRole.admin:
                        admin_user.role = UserRole.admin
                        updated = True
                    admin_user.password_hash = hash_password(settings.ADMIN_PASSWORD)
                    updated = True
                    if updated:
                        await db.commit()
                        await db.refresh(admin_user)
                        logger.info("admin.updated", email=admin_email)
    except Exception as e:
        logger.warning("admin.seed_failed", error=str(e))

    # Train the recommendation model on startup
    try:
        async with AsyncSessionLocal() as db:
            recommender = get_recommender()
            await recommender.train(db)
            logger.info("app.recommender_trained_on_startup")
    except Exception as e:
        logger.warning("app.recommender_train_failed_on_startup", error=str(e))

    # Optional: compute evaluation metrics on startup so UI can display graphs.
    # This can be somewhat expensive; keep it behind an env flag.
    try:
        if str(getattr(settings, "AUTO_EVALUATE_ON_STARTUP", "")).lower() in {"1", "true", "yes"}:
            async with AsyncSessionLocal() as db:
                gift_repo = GiftRepository(db)
                all_gifts = await gift_repo.get_all_gifts()
                gift_dicts = [
                    {
                        "id": g.id,
                        "title": g.title,
                        "description": g.description or "",
                        "occasion": g.occasion or "",
                        "relationship": g.relationship or "",
                        "category_name": g.category.name if g.category else "",
                        "tags": g.tags or "",
                        "age_group": getattr(g, "age_group", "") or "",
                        "price": g.price,
                    }
                    for g in all_gifts
                ]
                evaluator = RecommendationEvaluator(cross_validate=False)
                result = await evaluator.evaluate(db, gift_dicts, model_name="hybrid")
                logger.info(
                    "app.evaluation_complete_on_startup",
                    precision=result.precision,
                    recall=result.recall,
                    f1=result.f1_score,
                    accuracy=result.accuracy,
                )
    except Exception as e:
        logger.warning("app.evaluation_failed_on_startup", error=str(e))

    logger.info("app.started", name=settings.APP_NAME)
    yield

    logger.info("app.shutting_down")
    await engine.dispose()
    logger.info("app.shutdown_complete")


def create_application() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "AI-Enabled Gift Recommendation System with RAG, "
            "Hybrid Filtering, and Admin Dashboard. "
            "Masters Final Year Project."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # --- CORS ---
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Restrict in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Exception Handlers ---
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        errors = []
        for error in exc.errors():
            errors.append({
                "field": " -> ".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            })
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": "Validation error", "errors": errors},
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error("app.unhandled_exception", path=request.url.path, error=str(exc))
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An internal server error occurred."},
        )

    # --- Routes ---
    app.include_router(api_router)

    @app.get("/health", tags=["Health"])
    async def health_check():
        return {
            "status": "healthy",
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
        }

    @app.get("/", tags=["Root"])
    async def root():
        return {
            "message": f"Welcome to {settings.APP_NAME}",
            "version": settings.APP_VERSION,
            "docs": "/docs",
        }

    return app


app = create_application()
