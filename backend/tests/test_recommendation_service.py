"""
Unit tests for services/recommendation_service.py (currently ~26% coverage).
Tests InteractionService and RecommendationService with mocked dependencies.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException

from app.services.recommendation_service import InteractionService, RecommendationService
from app.schemas.recommendation import InteractionCreate, RecommendationWithGift
from app.models.models import (
    Interaction, InteractionType, Gift, Recommendation, ModelType, Category
)


# ---------------------------------------------------------------------------
# InteractionService
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_db():
    return AsyncMock()


def make_mock_gift(gift_id=1):
    gift = MagicMock(spec=Gift)
    gift.id = gift_id
    gift.title = "Test Gift"
    gift.description = "Desc"
    gift.price = 29.99
    gift.occasion = "Birthday"
    gift.relationship = "Friend"
    gift.image_url = "http://img.test/1.jpg"
    gift.product_url = "http://shop.test/1"
    gift.category = MagicMock()
    gift.category.name = "Electronics"
    return gift


@pytest.mark.asyncio
async def test_interaction_service_record_click(mock_db):
    mock_gift = make_mock_gift()
    mock_interaction = MagicMock(spec=Interaction)
    mock_interaction.id = 1
    mock_interaction.user_id = 1
    mock_interaction.gift_id = 1
    mock_interaction.interaction_type = InteractionType.click
    mock_interaction.rating = None

    mock_gift_repo = AsyncMock()
    mock_gift_repo.get_by_id.return_value = mock_gift

    mock_interaction_repo = AsyncMock()
    mock_interaction_repo.create.return_value = mock_interaction

    with patch("app.services.recommendation_service.GiftRepository", return_value=mock_gift_repo), \
         patch("app.services.recommendation_service.InteractionRepository", return_value=mock_interaction_repo):
        service = InteractionService(mock_db)
        payload = InteractionCreate(gift_id=1, interaction_type=InteractionType.click)
        result = await service.record_interaction(user_id=1, payload=payload)

    assert result.id == 1
    mock_interaction_repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_interaction_service_gift_not_found_raises_404(mock_db):
    mock_gift_repo = AsyncMock()
    mock_gift_repo.get_by_id.return_value = None
    mock_interaction_repo = AsyncMock()

    with patch("app.services.recommendation_service.GiftRepository", return_value=mock_gift_repo), \
         patch("app.services.recommendation_service.InteractionRepository", return_value=mock_interaction_repo):
        service = InteractionService(mock_db)
        payload = InteractionCreate(gift_id=9999, interaction_type=InteractionType.click)
        with pytest.raises(HTTPException) as exc_info:
            await service.record_interaction(user_id=1, payload=payload)

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_interaction_service_rating_requires_value(mock_db):
    mock_gift = make_mock_gift()
    mock_gift_repo = AsyncMock()
    mock_gift_repo.get_by_id.return_value = mock_gift
    mock_interaction_repo = AsyncMock()

    with patch("app.services.recommendation_service.GiftRepository", return_value=mock_gift_repo), \
         patch("app.services.recommendation_service.InteractionRepository", return_value=mock_interaction_repo):
        service = InteractionService(mock_db)
        payload = InteractionCreate(gift_id=1, interaction_type=InteractionType.rating, rating=None)
        with pytest.raises(HTTPException) as exc_info:
            await service.record_interaction(user_id=1, payload=payload)

    assert exc_info.value.status_code == 422


# ---------------------------------------------------------------------------
# RecommendationService
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_recommendation_service_returns_empty_when_recommender_gives_nothing(mock_db):
    mock_interaction_repo = AsyncMock()
    mock_interaction_repo.get_user_interactions.return_value = []

    mock_rec_repo = AsyncMock()
    mock_gift_repo = AsyncMock()

    mock_recommender = MagicMock()
    mock_recommender._trained = True
    mock_recommender.recommend.return_value = []

    mock_profile_repo = AsyncMock()
    mock_profile_repo.get_by_user_id.return_value = None

    with patch("app.services.recommendation_service.InteractionRepository", return_value=mock_interaction_repo), \
         patch("app.services.recommendation_service.RecommendationRepository", return_value=mock_rec_repo), \
         patch("app.services.recommendation_service.GiftRepository", return_value=mock_gift_repo), \
         patch("app.services.recommendation_service.UserProfileRepository", return_value=mock_profile_repo), \
         patch("app.services.recommendation_service.get_recommender", return_value=mock_recommender):
        service = RecommendationService(mock_db)
        result = await service.get_personalized_recommendations(user_id=1)

    assert result == []


@pytest.mark.asyncio
async def test_recommendation_service_trains_when_not_trained(mock_db):
    mock_interaction_repo = AsyncMock()
    mock_interaction_repo.get_user_interactions.return_value = []

    mock_rec_repo = AsyncMock()
    mock_gift_repo = AsyncMock()

    mock_recommender = MagicMock()
    mock_recommender._trained = False
    mock_recommender.train = AsyncMock()
    mock_recommender.recommend.return_value = []

    mock_profile_repo = AsyncMock()
    mock_profile_repo.get_by_user_id.return_value = None

    with patch("app.services.recommendation_service.InteractionRepository", return_value=mock_interaction_repo), \
         patch("app.services.recommendation_service.RecommendationRepository", return_value=mock_rec_repo), \
         patch("app.services.recommendation_service.GiftRepository", return_value=mock_gift_repo), \
         patch("app.services.recommendation_service.UserProfileRepository", return_value=mock_profile_repo), \
         patch("app.services.recommendation_service.get_recommender", return_value=mock_recommender):
        service = RecommendationService(mock_db)
        await service.get_personalized_recommendations(user_id=1)

    mock_recommender.train.assert_called_once()


@pytest.mark.asyncio
async def test_recommendation_service_returns_enriched_results(mock_db):
    mock_gift = make_mock_gift(gift_id=5)

    mock_interaction_repo = AsyncMock()
    mock_interaction_repo.get_user_interactions.return_value = []

    mock_rec_repo = AsyncMock()
    mock_rec_repo.delete_user_recommendations = AsyncMock(return_value=0)
    mock_rec_repo.bulk_create = AsyncMock(return_value=[])

    mock_gift_repo = AsyncMock()
    mock_gift_repo.get_all_gifts.return_value = [mock_gift]

    scored = [{"id": 5, "score": 0.95}]
    mock_recommender = MagicMock()
    mock_recommender._trained = True
    mock_recommender.recommend.return_value = scored

    mock_profile_repo = AsyncMock()
    mock_profile_repo.get_by_user_id.return_value = None

    with patch("app.services.recommendation_service.InteractionRepository", return_value=mock_interaction_repo), \
         patch("app.services.recommendation_service.RecommendationRepository", return_value=mock_rec_repo), \
         patch("app.services.recommendation_service.GiftRepository", return_value=mock_gift_repo), \
         patch("app.services.recommendation_service.UserProfileRepository", return_value=mock_profile_repo), \
         patch("app.services.recommendation_service.get_recommender", return_value=mock_recommender):
        service = RecommendationService(mock_db)
        results = await service.get_personalized_recommendations(user_id=1)

    assert len(results) == 1
    assert results[0].gift_id == 5
    assert results[0].score == pytest.approx(0.95)
    assert results[0].title == "Test Gift"


@pytest.mark.asyncio
async def test_recommendation_service_skips_missing_gift(mock_db):
    mock_interaction_repo = AsyncMock()
    mock_interaction_repo.get_user_interactions.return_value = []

    mock_rec_repo = AsyncMock()
    mock_rec_repo.delete_user_recommendations = AsyncMock(return_value=0)
    mock_rec_repo.bulk_create = AsyncMock(return_value=[])

    mock_gift_repo = AsyncMock()
    mock_gift_repo.get_all_gifts.return_value = []  # No gifts in map

    scored = [{"id": 999, "score": 0.8}]
    mock_recommender = MagicMock()
    mock_recommender._trained = True
    mock_recommender.recommend.return_value = scored

    mock_profile_repo = AsyncMock()
    mock_profile_repo.get_by_user_id.return_value = None

    with patch("app.services.recommendation_service.InteractionRepository", return_value=mock_interaction_repo), \
         patch("app.services.recommendation_service.RecommendationRepository", return_value=mock_rec_repo), \
         patch("app.services.recommendation_service.GiftRepository", return_value=mock_gift_repo), \
         patch("app.services.recommendation_service.UserProfileRepository", return_value=mock_profile_repo), \
         patch("app.services.recommendation_service.get_recommender", return_value=mock_recommender):
        service = RecommendationService(mock_db)
        results = await service.get_personalized_recommendations(user_id=1)

    assert results == []


@pytest.mark.asyncio
async def test_compare_models_includes_knowledge_and_clamped_metrics(mock_db):
    mock_gift = make_mock_gift(gift_id=10)

    mock_interaction_repo = AsyncMock()
    mock_interaction_repo.get_user_interactions.return_value = []

    mock_rec_repo = AsyncMock()

    mock_gift_repo = AsyncMock()
    mock_gift_repo.get_all_gifts.return_value = [mock_gift]

    mock_profile_repo = AsyncMock()
    mock_profile_repo.get_by_user_id.return_value = None

    mock_content_filter = MagicMock()
    mock_content_filter.get_scores_for_user_profile.return_value = [{"id": 10, "score": 2.5}]
    mock_content_filter.get_scores_for_query.return_value = [{"id": 10, "score": 2.5}]

    mock_collab_filter = MagicMock()
    mock_collab_filter.user_ids = [1]
    mock_collab_filter.get_scores_for_user.return_value = [{"id": 10, "score": 2.5}]

    mock_recommender = MagicMock()
    mock_recommender._trained = True
    mock_recommender.content_filter = mock_content_filter
    mock_recommender.collaborative_filter = mock_collab_filter
    mock_recommender.recommend.return_value = [{"id": 10, "score": 2.5}]
    mock_recommender.content_weight = 0.6
    mock_recommender.collaborative_weight = 0.4

    with patch("app.services.recommendation_service.InteractionRepository", return_value=mock_interaction_repo), \
         patch("app.services.recommendation_service.RecommendationRepository", return_value=mock_rec_repo), \
         patch("app.services.recommendation_service.GiftRepository", return_value=mock_gift_repo), \
         patch("app.services.recommendation_service.UserProfileRepository", return_value=mock_profile_repo), \
         patch("app.services.recommendation_service.get_recommender", return_value=mock_recommender), \
         patch("app.services.rag.rag_service.RAGService") as rag_cls, \
         patch("app.schemas.recommendation.RAGQueryCreate"):
        rag_cls.return_value.ask = AsyncMock(return_value={"response": "", "retrieved_gifts": []})
        service = RecommendationService(mock_db)
        response = await service.compare_all_models(user_id=1, top_n=2)

    models = {m.model for m in response.models}
    assert "knowledge" in models

    # Ensure metrics are clamped to [0, 1]
    for m in response.models:
        for key in ("precision", "recall", "f1", "coverage"):
            if key in m.metrics:
                assert 0.0 <= m.metrics[key] <= 1.0
        if m.gifts:
            g = m.gifts[0]
            assert hasattr(g, "is_valid_recommendation")
            assert hasattr(g, "query_cosine_similarity")
