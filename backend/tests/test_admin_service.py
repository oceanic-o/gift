"""
Unit tests for services/admin_service.py (currently ~38% coverage).
Uses mocked dependencies to avoid PostgreSQL.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.admin_service import AdminService
from app.schemas.recommendation import AdminStats


@pytest.fixture
def mock_db():
    return AsyncMock()


def _make_admin_service_with_mocks(mock_db):
    """Create AdminService with all repos mocked."""
    service = AdminService.__new__(AdminService)
    service.db = mock_db
    service.user_repo = AsyncMock()
    service.gift_repo = AsyncMock()
    service.interaction_repo = AsyncMock()
    service.rec_repo = AsyncMock()
    service.metric_repo = AsyncMock()
    service.category_repo = AsyncMock()
    return service


# ---------------------------------------------------------------------------
# get_stats
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_stats_returns_admin_stats(mock_db):
    service = _make_admin_service_with_mocks(mock_db)
    service.user_repo.count.return_value = 10
    service.gift_repo.count.return_value = 100
    service.interaction_repo.get_total_count.return_value = 50
    service.rec_repo.get_total_count.return_value = 30
    service.interaction_repo.get_interaction_counts_by_type.return_value = {"click": 20, "purchase": 15}
    service.metric_repo.get_best_model.return_value = None

    # Mock the raw DB execute for categories
    mock_result = MagicMock()
    mock_result.all.return_value = [("Electronics", 40), ("Books", 20)]
    mock_db.execute = AsyncMock(return_value=mock_result)

    stats = await service.get_stats()

    assert stats.total_users == 10
    assert stats.total_gifts == 100
    assert stats.total_interactions == 50
    assert stats.total_recommendations == 30
    assert len(stats.popular_categories) == 2
    assert stats.best_model is None


@pytest.mark.asyncio
async def test_get_stats_with_best_model(mock_db):
    from datetime import datetime, timezone
    service = _make_admin_service_with_mocks(mock_db)
    service.user_repo.count.return_value = 5
    service.gift_repo.count.return_value = 50
    service.interaction_repo.get_total_count.return_value = 20
    service.rec_repo.get_total_count.return_value = 10
    service.interaction_repo.get_interaction_counts_by_type.return_value = {}

    mock_metric = MagicMock()
    mock_metric.model_name = "hybrid"
    mock_metric.f1_score = 0.82
    mock_metric.precision = 0.85
    mock_metric.recall = 0.79
    mock_metric.accuracy = 0.88
    mock_metric.evaluated_at = datetime.now(timezone.utc)
    service.metric_repo.get_best_model.return_value = mock_metric

    mock_result = MagicMock()
    mock_result.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_result)

    stats = await service.get_stats()
    assert stats.best_model is not None
    assert stats.best_model["model_name"] == "hybrid"
    assert stats.best_model["f1_score"] == pytest.approx(0.82)


# ---------------------------------------------------------------------------
# get_all_metrics
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_all_metrics(mock_db):
    service = _make_admin_service_with_mocks(mock_db)
    service.metric_repo.get_all_metrics.return_value = []
    result = await service.get_all_metrics()
    assert result == []
    service.metric_repo.get_all_metrics.assert_called_once()


# ---------------------------------------------------------------------------
# get_all_users
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_all_users(mock_db):
    service = _make_admin_service_with_mocks(mock_db)
    mock_user = MagicMock()
    mock_user.email = "admin@test.com"
    service.user_repo.get_all_users.return_value = [mock_user]

    result = await service.get_all_users(skip=0, limit=10)
    assert len(result) == 1
    service.user_repo.get_all_users.assert_called_once_with(skip=0, limit=10)


# ---------------------------------------------------------------------------
# update_user_role
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_user_role(mock_db):
    from app.models.models import UserRole

    service = _make_admin_service_with_mocks(mock_db)
    mock_user = MagicMock()
    mock_user.role = UserRole.user
    service.user_repo.get_by_id.return_value = mock_user

    result = await service.update_user_role(user_id=123, role=UserRole.admin)

    assert result.role == UserRole.admin
    service.user_repo.get_by_id.assert_called_once_with(123)
    mock_db.flush.assert_called_once()


# ---------------------------------------------------------------------------
# get_all_interactions
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_all_interactions(mock_db):
    service = _make_admin_service_with_mocks(mock_db)
    service.interaction_repo.get_all_paginated.return_value = []

    result = await service.get_all_interactions(skip=0, limit=50)
    assert result == []
    service.interaction_repo.get_all_paginated.assert_called_once_with(skip=0, limit=50)


# ---------------------------------------------------------------------------
# retrain_model
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_retrain_model(mock_db):
    service = _make_admin_service_with_mocks(mock_db)

    mock_recommender = MagicMock()
    mock_recommender.train = AsyncMock()

    with patch("app.services.admin_service.get_recommender", return_value=mock_recommender):
        result = await service.retrain_model()

    assert result["message"] == "Model retrained successfully."
    mock_recommender.train.assert_called_once_with(mock_db)


# ---------------------------------------------------------------------------
# evaluate_model
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_evaluate_model(mock_db):
    service = _make_admin_service_with_mocks(mock_db)

    expected = {
        "message": "All model evaluations completed.",
        "mode": "profile_context_batch",
        "users_evaluated": 1,
        "results": [{"model_name": "hybrid", "f1_score": 0.77}],
    }
    service._evaluate_all_models_contextual = AsyncMock(return_value=expected)

    result = await service.evaluate_model()

    assert result == expected
    service._evaluate_all_models_contextual.assert_called_once_with(max_users=1, top_n=6)
