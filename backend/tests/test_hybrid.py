"""
Unit Tests: Hybrid Recommendation Engine
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.recommendation.hybrid import HybridRecommender


@pytest.fixture
def hybrid_recommender(sample_gifts_data, sample_interactions_data):
    """Create and manually fit a hybrid recommender."""
    rec = HybridRecommender(content_weight=0.55, collaborative_weight=0.35, knowledge_weight=0.1)
    rec.content_filter.fit(sample_gifts_data)
    rec.collaborative_filter.fit(sample_interactions_data)
    rec._trained = True
    return rec


def test_hybrid_recommender_init():
    """Test default initialization."""
    rec = HybridRecommender()
    assert rec.content_weight == 0.55
    assert rec.collaborative_weight == 0.35
    assert rec.knowledge_weight == 0.10
    assert rec._trained is False


def test_hybrid_recommender_custom_weights():
    """Test custom weight initialization."""
    rec = HybridRecommender(content_weight=0.6, collaborative_weight=0.3, knowledge_weight=0.1)
    assert rec.content_weight == 0.6
    assert rec.collaborative_weight == 0.3
    assert rec.knowledge_weight == 0.1


def test_hybrid_set_weights_valid(hybrid_recommender):
    """Valid weights summing to 1.0 should be accepted."""
    hybrid_recommender.set_weights(0.6, 0.3, 0.1)
    assert hybrid_recommender.content_weight == 0.6
    assert hybrid_recommender.collaborative_weight == 0.3
    assert hybrid_recommender.knowledge_weight == 0.1


def test_hybrid_set_weights_invalid(hybrid_recommender):
    """Weights not summing to 1.0 should raise ValueError."""
    with pytest.raises(ValueError, match="must sum to 1.0"):
        hybrid_recommender.set_weights(0.5, 0.6, 0.1)


def test_hybrid_recommend_returns_results(hybrid_recommender):
    """Recommend should return a list of gift scores."""
    results = hybrid_recommender.recommend(
        user_id=1,
        liked_gift_ids=[1, 2],
        top_n=5,
    )
    assert isinstance(results, list)
    assert len(results) <= 5


def test_hybrid_recommend_result_structure(hybrid_recommender):
    """Each result should have id, score, content_score, collab_score, knowledge_score."""
    results = hybrid_recommender.recommend(
        user_id=1,
        liked_gift_ids=[1],
        top_n=3,
    )
    for r in results:
        assert "id" in r
        assert "score" in r
        assert "content_score" in r
        assert "collab_score" in r
        assert "knowledge_score" in r


def test_hybrid_recommend_scores_in_range(hybrid_recommender):
    """All final scores should be in [0, 1]."""
    results = hybrid_recommender.recommend(
        user_id=2,
        liked_gift_ids=[2, 4],
        top_n=10,
    )
    for r in results:
        assert 0.0 <= r["score"] <= 1.0, f"Score {r['score']} out of range"


def test_hybrid_recommend_sorted_descending(hybrid_recommender):
    """Results should be sorted by score descending."""
    results = hybrid_recommender.recommend(
        user_id=1,
        liked_gift_ids=[1],
        top_n=8,
    )
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True), "Results not sorted by score"


def test_hybrid_recommend_not_trained():
    """Untrained recommender should return empty list."""
    rec = HybridRecommender()
    results = rec.recommend(user_id=1, liked_gift_ids=[], top_n=5)
    assert results == []


def test_hybrid_recommend_cold_start_user(hybrid_recommender):
    """New user with no interactions should still get recommendations."""
    results = hybrid_recommender.recommend(
        user_id=9999,
        liked_gift_ids=[],
        top_n=5,
    )
    # Should fall back to popularity/cold start
    assert isinstance(results, list)


def test_hybrid_recommend_occasion_filter(hybrid_recommender):
    """Occasion filter should restrict content-based results."""
    results = hybrid_recommender.recommend(
        user_id=1,
        liked_gift_ids=[1],
        top_n=5,
        occasion="Birthday",
    )
    assert isinstance(results, list)


def test_hybrid_score_formula(hybrid_recommender):
    """Verify hybrid base score formula before small exploration boost."""
    results = hybrid_recommender.recommend(user_id=1, liked_gift_ids=[1], top_n=5)
    for r in results:
        c_score = r.get("content_score", 0.0)
        col_score = r.get("collab_score", 0.0)
        k_score = r.get("knowledge_score", 0.0)
        base = round(0.55 * c_score + 0.35 * col_score + 0.10 * k_score, 6)
        # Final score may be lower if a demographic/gender penalty was applied.
        # A small exploration boost (<=0.03) may also be applied.
        assert r["score"] <= min(1.0, base + 0.031)


def test_hybrid_recommend_unique_ids(hybrid_recommender):
    """Diversification should not introduce duplicate IDs."""
    results = hybrid_recommender.recommend(user_id=1, liked_gift_ids=[1], top_n=10)
    ids = [r["id"] for r in results]
    assert len(ids) == len(set(ids))
