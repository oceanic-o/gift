"""
Unit tests for repositories: BaseRepository, GiftRepository,
CategoryRepository, UserRepository, InteractionRepository,
RecommendationRepository, ModelMetricRepository.

Uses in-memory SQLite via the db_session fixture from conftest.py.
"""
import pytest
from app.repositories.base import BaseRepository
from app.repositories.gift_repository import GiftRepository, CategoryRepository
from app.repositories.user_repository import UserRepository
from app.repositories.interaction_repository import (
    InteractionRepository, RecommendationRepository, ModelMetricRepository
)
from app.models.models import (
    User, UserRole, Category, Gift,
    Interaction, InteractionType, Recommendation, ModelType, ModelMetric
)
from app.core.security import hash_password
from app.schemas.gift import GiftFilterParams


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def make_category(db, name="Electronics"):
    cat = Category(name=name)
    db.add(cat)
    await db.flush()
    await db.refresh(cat)
    return cat


async def make_gift(db, category_id, title="Watch", price=99.99):
    gift = Gift(title=title, category_id=category_id, price=price)
    db.add(gift)
    await db.flush()
    await db.refresh(gift)
    return gift


async def make_user(db, email="u@test.com"):
    user = User(
        name="Test User",
        email=email,
        password_hash=hash_password("Pass123!"),
        role=UserRole.user,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


# ---------------------------------------------------------------------------
# BaseRepository
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_base_get_by_id_existing(db_session):
    cat = await make_category(db_session, "Books")
    repo = BaseRepository(Category, db_session)
    found = await repo.get_by_id(cat.id)
    assert found is not None
    assert found.name == "Books"


@pytest.mark.asyncio
async def test_base_get_by_id_missing(db_session):
    repo = BaseRepository(Category, db_session)
    result = await repo.get_by_id(99999)
    assert result is None


@pytest.mark.asyncio
async def test_base_get_all(db_session):
    await make_category(db_session, "Cat1")
    await make_category(db_session, "Cat2")
    repo = BaseRepository(Category, db_session)
    all_cats = await repo.get_all()
    assert len(all_cats) >= 2


@pytest.mark.asyncio
async def test_base_create(db_session):
    repo = BaseRepository(Category, db_session)
    cat = Category(name="NewCat")
    created = await repo.create(cat)
    assert created.id is not None


@pytest.mark.asyncio
async def test_base_delete_existing(db_session):
    cat = await make_category(db_session, "ToDelete")
    repo = BaseRepository(Category, db_session)
    result = await repo.delete(cat.id)
    assert result is True


@pytest.mark.asyncio
async def test_base_delete_nonexistent(db_session):
    repo = BaseRepository(Category, db_session)
    result = await repo.delete(99999)
    assert result is False


@pytest.mark.asyncio
async def test_base_count(db_session):
    await make_category(db_session, "C1")
    await make_category(db_session, "C2")
    repo = BaseRepository(Category, db_session)
    count = await repo.count()
    assert count >= 2


# ---------------------------------------------------------------------------
# CategoryRepository
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_category_repo_get_by_name_existing(db_session):
    await make_category(db_session, "Sports")
    repo = CategoryRepository(db_session)
    found = await repo.get_by_name("Sports")
    assert found is not None
    assert found.name == "Sports"


@pytest.mark.asyncio
async def test_category_repo_get_by_name_missing(db_session):
    repo = CategoryRepository(db_session)
    result = await repo.get_by_name("NonExistent")
    assert result is None


@pytest.mark.asyncio
async def test_category_repo_get_or_create_new(db_session):
    repo = CategoryRepository(db_session)
    cat, created = await repo.get_or_create("BrandNew")
    assert created is True
    assert cat.name == "BrandNew"


@pytest.mark.asyncio
async def test_category_repo_get_or_create_existing(db_session):
    await make_category(db_session, "Existing")
    repo = CategoryRepository(db_session)
    cat, created = await repo.get_or_create("Existing")
    assert created is False
    assert cat.name == "Existing"


# ---------------------------------------------------------------------------
# GiftRepository
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_gift_repo_get_with_category(db_session):
    cat = await make_category(db_session, "Gadgets")
    gift = await make_gift(db_session, cat.id, "Smartwatch")
    repo = GiftRepository(db_session)
    found = await repo.get_with_category(gift.id)
    assert found is not None
    assert found.title == "Smartwatch"


@pytest.mark.asyncio
async def test_gift_repo_get_with_category_missing(db_session):
    repo = GiftRepository(db_session)
    result = await repo.get_with_category(99999)
    assert result is None


@pytest.mark.asyncio
async def test_gift_repo_get_all_with_filters_no_filter(db_session):
    cat = await make_category(db_session, "Misc")
    await make_gift(db_session, cat.id, "G1", price=10.0)
    await make_gift(db_session, cat.id, "G2", price=20.0)
    repo = GiftRepository(db_session)
    params = GiftFilterParams()
    results = await repo.get_all_with_filters(params)
    assert len(results) >= 2


@pytest.mark.asyncio
async def test_gift_repo_get_all_with_filters_price(db_session):
    cat = await make_category(db_session, "Priced")
    await make_gift(db_session, cat.id, "Cheap", price=5.0)
    await make_gift(db_session, cat.id, "Pricy", price=500.0)
    repo = GiftRepository(db_session)
    params = GiftFilterParams(max_price=50.0)
    results = await repo.get_all_with_filters(params)
    assert all(g.price <= 50.0 for g in results)


@pytest.mark.asyncio
async def test_gift_repo_get_all_gifts(db_session):
    cat = await make_category(db_session, "All")
    await make_gift(db_session, cat.id, "GA")
    await make_gift(db_session, cat.id, "GB")
    repo = GiftRepository(db_session)
    results = await repo.get_all_gifts()
    assert len(results) >= 2


# ---------------------------------------------------------------------------
# UserRepository
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_user_repo_get_by_email_existing(db_session):
    await make_user(db_session, "findme@test.com")
    repo = UserRepository(db_session)
    found = await repo.get_by_email("findme@test.com")
    assert found is not None
    assert found.email == "findme@test.com"


@pytest.mark.asyncio
async def test_user_repo_get_by_email_missing(db_session):
    repo = UserRepository(db_session)
    result = await repo.get_by_email("nobody@test.com")
    assert result is None


@pytest.mark.asyncio
async def test_user_repo_email_exists_true(db_session):
    await make_user(db_session, "exists@test.com")
    repo = UserRepository(db_session)
    assert await repo.email_exists("exists@test.com") is True


@pytest.mark.asyncio
async def test_user_repo_email_exists_false(db_session):
    repo = UserRepository(db_session)
    assert await repo.email_exists("nope@test.com") is False


@pytest.mark.asyncio
async def test_user_repo_get_all_users(db_session):
    await make_user(db_session, "u1@test.com")
    await make_user(db_session, "u2@test.com")
    repo = UserRepository(db_session)
    users = await repo.get_all_users()
    assert len(users) >= 2


@pytest.mark.asyncio
async def test_user_repo_get_by_id(db_session):
    user = await make_user(db_session, "byid@test.com")
    repo = UserRepository(db_session)
    found = await repo.get_by_id(user.id)
    assert found is not None
    assert found.id == user.id


# ---------------------------------------------------------------------------
# InteractionRepository
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_interaction_repo_create_and_fetch(db_session):
    cat = await make_category(db_session, "InterCat")
    gift = await make_gift(db_session, cat.id)
    user = await make_user(db_session, "inter@test.com")

    repo = InteractionRepository(db_session)
    interaction = Interaction(
        user_id=user.id,
        gift_id=gift.id,
        interaction_type=InteractionType.click,
    )
    created = await repo.create(interaction)
    assert created.id is not None

    interactions = await repo.get_user_interactions(user.id)
    assert len(interactions) == 1
    assert interactions[0].gift_id == gift.id


@pytest.mark.asyncio
async def test_interaction_repo_get_all_for_matrix(db_session):
    cat = await make_category(db_session, "MatCat")
    gift = await make_gift(db_session, cat.id)
    user = await make_user(db_session, "mat@test.com")
    repo = InteractionRepository(db_session)
    inter = Interaction(
        user_id=user.id, gift_id=gift.id,
        interaction_type=InteractionType.rating, rating=4.0
    )
    await repo.create(inter)
    all_inters = await repo.get_all_interactions_for_matrix()
    assert len(all_inters) >= 1


@pytest.mark.asyncio
async def test_interaction_repo_get_total_count(db_session):
    cat = await make_category(db_session, "CountCat")
    gift = await make_gift(db_session, cat.id)
    user = await make_user(db_session, "count@test.com")
    repo = InteractionRepository(db_session)
    inter = Interaction(
        user_id=user.id, gift_id=gift.id,
        interaction_type=InteractionType.purchase
    )
    await repo.create(inter)
    count = await repo.get_total_count()
    assert count >= 1


@pytest.mark.asyncio
async def test_interaction_repo_user_has_interaction(db_session):
    cat = await make_category(db_session, "HasCat")
    gift = await make_gift(db_session, cat.id)
    user = await make_user(db_session, "has@test.com")
    repo = InteractionRepository(db_session)
    inter = Interaction(
        user_id=user.id, gift_id=gift.id,
        interaction_type=InteractionType.click
    )
    await repo.create(inter)
    assert await repo.user_has_interaction(user.id, gift.id) is True
    assert await repo.user_has_interaction(user.id, 99999) is False


@pytest.mark.asyncio
async def test_interaction_repo_interaction_counts_by_type(db_session):
    cat = await make_category(db_session, "TypeCat")
    gift = await make_gift(db_session, cat.id)
    user = await make_user(db_session, "type@test.com")
    repo = InteractionRepository(db_session)
    await repo.create(Interaction(
        user_id=user.id, gift_id=gift.id, interaction_type=InteractionType.click
    ))
    await repo.create(Interaction(
        user_id=user.id, gift_id=gift.id, interaction_type=InteractionType.purchase
    ))
    counts = await repo.get_interaction_counts_by_type()
    assert isinstance(counts, dict)


# ---------------------------------------------------------------------------
# RecommendationRepository
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_recommendation_repo_bulk_create(db_session):
    cat = await make_category(db_session, "RecCat")
    gift = await make_gift(db_session, cat.id)
    user = await make_user(db_session, "rec@test.com")
    repo = RecommendationRepository(db_session)
    recs = [
        Recommendation(user_id=user.id, gift_id=gift.id, score=0.9, model_type=ModelType.hybrid)
    ]
    created = await repo.bulk_create(recs)
    assert len(created) == 1


@pytest.mark.asyncio
async def test_recommendation_repo_get_total_count(db_session):
    cat = await make_category(db_session, "TotCat")
    gift = await make_gift(db_session, cat.id)
    user = await make_user(db_session, "tot@test.com")
    repo = RecommendationRepository(db_session)
    await repo.bulk_create([
        Recommendation(user_id=user.id, gift_id=gift.id, score=0.8, model_type=ModelType.hybrid)
    ])
    count = await repo.get_total_count()
    assert count >= 1


@pytest.mark.asyncio
async def test_recommendation_repo_delete_user_recommendations(db_session):
    cat = await make_category(db_session, "DelCat")
    gift = await make_gift(db_session, cat.id)
    user = await make_user(db_session, "del@test.com")
    repo = RecommendationRepository(db_session)
    await repo.bulk_create([
        Recommendation(user_id=user.id, gift_id=gift.id, score=0.7, model_type=ModelType.hybrid)
    ])
    deleted = await repo.delete_user_recommendations(user.id)
    assert deleted == 1


# ---------------------------------------------------------------------------
# ModelMetricRepository
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_metric_repo_get_best_model_empty(db_session):
    repo = ModelMetricRepository(db_session)
    result = await repo.get_best_model()
    assert result is None


@pytest.mark.asyncio
async def test_metric_repo_get_all_metrics_empty(db_session):
    repo = ModelMetricRepository(db_session)
    results = await repo.get_all_metrics()
    assert results == []


@pytest.mark.asyncio
async def test_metric_repo_get_latest_by_model_empty(db_session):
    repo = ModelMetricRepository(db_session)
    result = await repo.get_latest_by_model("hybrid")
    assert result is None


@pytest.mark.asyncio
async def test_metric_repo_create_and_get_best(db_session):
    repo = ModelMetricRepository(db_session)
    m1 = ModelMetric(
        model_name="hybrid",
        precision=0.8, recall=0.7, f1_score=0.75, accuracy=0.8
    )
    m2 = ModelMetric(
        model_name="content",
        precision=0.6, recall=0.5, f1_score=0.55, accuracy=0.6
    )
    await repo.create(m1)
    await repo.create(m2)
    best = await repo.get_best_model()
    assert best.model_name == "hybrid"


@pytest.mark.asyncio
async def test_metric_repo_get_all_metrics(db_session):
    repo = ModelMetricRepository(db_session)
    await repo.create(ModelMetric(
        model_name="test_model",
        precision=0.5, recall=0.5, f1_score=0.5, accuracy=0.5
    ))
    results = await repo.get_all_metrics()
    assert len(results) >= 1


@pytest.mark.asyncio
async def test_metric_repo_get_latest_by_model(db_session):
    repo = ModelMetricRepository(db_session)
    await repo.create(ModelMetric(
        model_name="hybrid", precision=0.7, recall=0.6, f1_score=0.65, accuracy=0.7
    ))
    latest = await repo.get_latest_by_model("hybrid")
    assert latest is not None
    assert latest.model_name == "hybrid"
