from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import User, Interaction, Gift, InteractionType
from app.schemas.user_profile import (
    UserProfileUpdate,
    UserProfileResponse,
    PasswordChangeRequest,
    UserPreferencesUpdate,
    PublicReviewResponse,
)
from app.schemas.recommendation import RecommendationWithGift
from app.services.user_profile_service import UserProfileService
from app.services.recommendation_service import RecommendationService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me/profile", response_model=UserProfileResponse | None)
async def get_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = UserProfileService(db)
    return await service.get_profile(current_user.id)


@router.put("/me/profile", response_model=UserProfileResponse)
async def update_profile(
    payload: UserProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = UserProfileService(db)
    return await service.upsert_profile(current_user.id, payload)


@router.post("/me/preferences", response_model=UserProfileResponse)
async def update_preferences(
    payload: UserPreferencesUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update onboarding preferences for the current user."""
    service = UserProfileService(db)
    return await service.upsert_profile(current_user.id, payload)


@router.post("/me/password")
async def change_password(
    payload: PasswordChangeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = UserProfileService(db)
    await service.change_password(current_user.id, payload)
    return {"message": "Password updated."}


@router.get("/me/home-recommendations", response_model=list[RecommendationWithGift])
async def home_recommendations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = RecommendationService(db)
    return await service.get_home_recommendations(current_user.id)


@router.get("/public-reviews", response_model=list[PublicReviewResponse])
async def get_public_reviews(
    limit: int = Query(6, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
):
    """Public recent user ratings, transformed into review cards for landing page."""
    result = await db.execute(
        select(Interaction, User.name, Gift.title)
        .join(User, Interaction.user_id == User.id)
        .join(Gift, Interaction.gift_id == Gift.id)
        .where(
            Interaction.interaction_type.in_(
                [
                    InteractionType.rating,
                    InteractionType.purchase,
                    InteractionType.click,
                ]
            ),
        )
        .order_by(Interaction.timestamp.desc())
        .limit(limit * 8)
    )
    rows = result.all()

    reviews: list[PublicReviewResponse] = []
    for interaction, user_name, gift_title in rows:
        display_name = (user_name or "User").strip() or "User"
        parts = display_name.split()
        if len(parts) >= 2:
            name = f"{parts[0]} {parts[1][0]}."
        else:
            name = parts[0]
        avatar = (parts[0][0] if parts and parts[0] else "U").upper()
        if interaction.interaction_type == InteractionType.rating and interaction.rating is not None:
            rating = max(1, min(5, int(round(float(interaction.rating)))))
            review_text = (
                f'Rated "{gift_title}" {rating}/5 after using Upahaar recommendations.'
            )
        elif interaction.interaction_type == InteractionType.purchase:
            rating = 5
            review_text = (
                f'Purchased "{gift_title}" after getting it from Upahaar recommendations.'
            )
        else:
            rating = 4
            review_text = (
                f'Explored "{gift_title}" through Upahaar recommendations.'
            )

        reviews.append(
            PublicReviewResponse(
                name=name,
                role="Verified User",
                avatar=avatar,
                rating=rating,
                review=review_text,
                reviewed_at=interaction.timestamp,
            )
        )
        if len(reviews) >= limit:
            break

    return reviews
