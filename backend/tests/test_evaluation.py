"""
Unit Tests: Evaluation Module
"""
import pytest
from app.services.evaluation.evaluator import RecommendationEvaluator


def test_evaluator_build_relevance():
    """Test binary relevance assignment."""
    evaluator = RecommendationEvaluator()
    interactions = [
        {"user_id": 1, "gift_id": 1, "interaction_type": "purchase", "rating": None},
        {"user_id": 1, "gift_id": 2, "interaction_type": "rating", "rating": 4.0},
        {"user_id": 1, "gift_id": 3, "interaction_type": "rating", "rating": 2.0},
        {"user_id": 1, "gift_id": 4, "interaction_type": "click", "rating": None},
    ]
    df = evaluator._build_relevance(interactions)

    assert df[df["gift_id"] == 1]["relevant"].values[0] == 1  # purchase → relevant
    assert df[df["gift_id"] == 2]["relevant"].values[0] == 1  # rating >= 3 → relevant
    assert df[df["gift_id"] == 3]["relevant"].values[0] == 0  # rating < 3 → not relevant
    assert df[df["gift_id"] == 4]["relevant"].values[0] == 0  # click → not relevant


def test_evaluator_evaluate_split(sample_gifts_data, sample_interactions_data):
    """Test evaluate_split returns valid binary arrays."""
    evaluator = RecommendationEvaluator(top_n=5)
    train = sample_interactions_data[:12]
    test = sample_interactions_data[12:]

    y_true, y_pred = evaluator._evaluate_split(train, test, sample_gifts_data)

    assert isinstance(y_true, list)
    assert isinstance(y_pred, list)
    assert len(y_true) == len(y_pred)

    # All values should be binary
    assert all(v in (0, 1) for v in y_true)
    assert all(v in (0, 1) for v in y_pred)


def test_evaluator_empty_test_split(sample_gifts_data):
    """Empty test set should return empty arrays."""
    evaluator = RecommendationEvaluator(top_n=5)
    train = [{"user_id": 1, "gift_id": 1, "interaction_type": "purchase", "rating": None}]
    test = []

    y_true, y_pred = evaluator._evaluate_split(train, test, sample_gifts_data)
    assert y_true == []
    assert y_pred == []


def test_evaluator_cross_validate(sample_gifts_data, sample_interactions_data):
    """Cross-validation should return fold scores."""
    evaluator = RecommendationEvaluator(top_n=3, cross_validate=True, n_folds=3)
    scores = evaluator._cross_validate(sample_interactions_data, sample_gifts_data)

    assert isinstance(scores, list)
    for score in scores:
        assert 0.0 <= score <= 1.0
