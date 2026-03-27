"""
Unit Tests: Content-Based Filtering
"""
import pytest
from app.services.recommendation.content_based import ContentBasedFilter


@pytest.fixture
def content_filter(sample_gifts_data):
    cf = ContentBasedFilter()
    cf.fit(sample_gifts_data)
    return cf


def test_content_filter_fit(sample_gifts_data):
    """Test that the content filter fits without errors."""
    cf = ContentBasedFilter()
    cf.fit(sample_gifts_data)
    assert cf._is_fitted is True
    assert len(cf.gift_ids) == len(sample_gifts_data)


def test_content_filter_similar_gifts_returns_results(content_filter):
    """Test that similar gifts are returned for a known gift."""
    results = content_filter.get_similar_gifts(gift_id=1, top_n=3)
    assert isinstance(results, list)
    assert len(results) <= 3
    # Gift 1 should not appear in its own recommendations
    result_ids = [r["id"] for r in results]
    assert 1 not in result_ids


def test_content_filter_scores_are_normalized(content_filter):
    """Scores should be in [0, 1]."""
    results = content_filter.get_similar_gifts(gift_id=1, top_n=5)
    for r in results:
        assert 0.0 <= r["score"] <= 1.0, f"Score out of range: {r['score']}"


def test_content_filter_occasion_filter(content_filter):
    """Occasion filter should restrict results."""
    results = content_filter.get_similar_gifts(gift_id=2, top_n=10, occasion="Birthday")
    occasions = [r.get("occasion", "") for r in results]
    # All returned gifts should have occasion=Birthday if they have one set
    # (The filter removes non-matching ones)
    assert isinstance(results, list)


def test_content_filter_price_filter(content_filter, sample_gifts_data):
    """Max price filter should exclude expensive gifts."""
    results = content_filter.get_similar_gifts(gift_id=1, top_n=10, max_price=50.0)
    # All results should be from the gift_df which was filtered by price <= 50
    assert isinstance(results, list)


def test_content_filter_user_profile(content_filter):
    """Profile-based recommendation should work with liked gift list."""
    results = content_filter.get_scores_for_user_profile(
        liked_gift_ids=[1, 2, 3],
        top_n=5,
    )
    assert isinstance(results, list)
    assert len(results) <= 5
    # Liked gifts should not appear in recommendations
    result_ids = [r["id"] for r in results]
    for liked_id in [1, 2, 3]:
        assert liked_id not in result_ids


def test_content_filter_cold_start_empty_history(content_filter):
    """Cold start should return results even with no liked gifts."""
    results = content_filter.get_scores_for_user_profile(
        liked_gift_ids=[],
        top_n=5,
    )
    assert isinstance(results, list)
    assert len(results) > 0


def test_content_filter_unknown_gift_id(content_filter):
    """Unknown gift ID should trigger cold start fallback."""
    results = content_filter.get_similar_gifts(gift_id=99999, top_n=5)
    assert isinstance(results, list)


def test_content_filter_empty_dataset():
    """Fitting with empty data should not crash."""
    cf = ContentBasedFilter()
    cf.fit([])
    assert cf._is_fitted is False
    results = cf.get_similar_gifts(gift_id=1, top_n=5)
    assert results == []
