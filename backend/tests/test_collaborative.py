"""
Unit Tests: Collaborative Filtering
"""
import pytest
from app.services.recommendation.collaborative import CollaborativeFilter


@pytest.fixture
def collab_filter(sample_interactions_data):
    cf = CollaborativeFilter()
    cf.fit(sample_interactions_data)
    return cf


def test_collab_filter_fit(sample_interactions_data):
    """Test that collaborative filter fits successfully."""
    cf = CollaborativeFilter()
    cf.fit(sample_interactions_data)
    assert cf._is_fitted is True
    assert len(cf.user_ids) > 0
    assert len(cf.gift_ids) > 0


def test_collab_filter_matrix_shape(collab_filter):
    """Matrix dimensions should match unique users × unique gifts."""
    n_users = len(collab_filter.user_ids)
    n_gifts = len(collab_filter.gift_ids)
    assert collab_filter.user_item_matrix.shape == (n_users, n_gifts)


def test_collab_filter_known_user(collab_filter):
    """Known user should get recommendations."""
    results = collab_filter.get_scores_for_user(user_id=1, top_n=5)
    assert isinstance(results, list)
    assert len(results) <= 5


def test_collab_filter_scores_normalized(collab_filter):
    """Scores should be in [0, 1]."""
    results = collab_filter.get_scores_for_user(user_id=1, top_n=10)
    for r in results:
        assert 0.0 <= r["score"] <= 1.0, f"Score out of range: {r['score']}"


def test_collab_filter_diversity_rerank_does_not_crash(collab_filter):
    """Diversity re-ranking should be stable and keep result size."""
    results = collab_filter.get_scores_for_user(
        user_id=1,
        top_n=7,
        diversity_lambda=0.6,
        candidate_pool=50,
    )
    assert isinstance(results, list)
    assert len(results) <= 7


def test_collab_filter_excludes_seen_gifts(collab_filter, sample_interactions_data):
    """User should not receive gifts they've already interacted with."""
    user_id = 1
    # Find gifts user 1 has interacted with
    user_gifts = {i["gift_id"] for i in sample_interactions_data if i["user_id"] == user_id}

    results = collab_filter.get_scores_for_user(user_id=user_id, top_n=10)
    result_ids = {r["id"] for r in results}

    # Seen gifts should not appear
    overlap = user_gifts & result_ids
    assert len(overlap) == 0, f"Seen gifts appeared in recommendations: {overlap}"


def test_collab_filter_unknown_user_fallback(collab_filter):
    """Unknown user should get popularity-based fallback."""
    results = collab_filter.get_scores_for_user(user_id=99999, top_n=5)
    assert isinstance(results, list)
    assert len(results) > 0  # Popularity fallback returns results


def test_collab_filter_interaction_weights():
    """Purchase interactions should create higher matrix values than clicks."""
    purchase_interactions = [
        {"user_id": 1, "gift_id": 1, "interaction_type": "purchase", "rating": None},
    ]
    click_interactions = [
        {"user_id": 2, "gift_id": 1, "interaction_type": "click", "rating": None},
    ]
    cf_purchase = CollaborativeFilter()
    cf_purchase.fit(purchase_interactions)

    cf_click = CollaborativeFilter()
    cf_click.fit(click_interactions)

    # Purchase weight (3.0) > click weight (1.0)
    purchase_val = cf_purchase.user_item_matrix[0, 0]
    click_val = cf_click.user_item_matrix[0, 0]
    assert purchase_val > click_val


def test_collab_filter_empty_interactions():
    """Empty interaction list should not crash."""
    cf = CollaborativeFilter()
    cf.fit([])
    assert cf._is_fitted is False
    results = cf.get_scores_for_user(user_id=1)
    assert results == []
