"""
Unit Tests: Knowledge-Based Recommendation
"""
import pytest
from app.services.recommendation.knowledge_based import KnowledgeBasedRecommender


@pytest.fixture
def kb():
    return KnowledgeBasedRecommender()


def test_knowledge_based_returns_results(kb, sample_gifts_data):
    results = kb.score_gifts(
        gifts=sample_gifts_data,
        top_n=5,
        occasion="Birthday",
        relationship="Friend",
        query_text="gift for friend who likes gadgets",
    )
    assert isinstance(results, list)
    assert len(results) <= 5


def test_knowledge_based_scores_in_range(kb, sample_gifts_data):
    results = kb.score_gifts(
        gifts=sample_gifts_data,
        top_n=10,
        query_text="yoga fitness wellness",
    )
    for r in results:
        assert 0.0 <= r["score"] <= 1.0


def test_knowledge_based_fallback(kb, sample_gifts_data):
    results = kb.score_gifts(
        gifts=sample_gifts_data,
        top_n=3,
        query_text="",
        occasion=None,
        relationship=None,
    )
    assert len(results) > 0
