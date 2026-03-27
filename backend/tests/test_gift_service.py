"""
Unit tests for services/gift_service.py (currently ~35% coverage).
Uses the in-memory SQLite db_session fixture.
"""
import pytest
from fastapi import HTTPException

from app.services.gift_service import GiftService
from app.schemas.gift import GiftCreate, GiftUpdate, CategoryCreate, GiftFilterParams
from app.models.models import Category


@pytest.fixture
async def category(db_session):
    """Pre-create a category for gift tests."""
    cat = Category(name="Electronics")
    db_session.add(cat)
    await db_session.flush()
    await db_session.refresh(cat)
    return cat


@pytest.fixture
async def gift_service(db_session):
    return GiftService(db_session)


# ---------------------------------------------------------------------------
# CategoryService via GiftService
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_category_success(gift_service):
    payload = CategoryCreate(name="Books")
    result = await gift_service.create_category(payload)
    assert result.name == "Books"
    assert result.id is not None


@pytest.mark.asyncio
async def test_create_category_duplicate_raises_409(gift_service):
    payload = CategoryCreate(name="Duplicate Cat")
    await gift_service.create_category(payload)
    with pytest.raises(HTTPException) as exc_info:
        await gift_service.create_category(payload)
    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_list_categories_empty(gift_service):
    result = await gift_service.list_categories()
    assert result == []


@pytest.mark.asyncio
async def test_list_categories_with_data(gift_service):
    await gift_service.create_category(CategoryCreate(name="Sports"))
    await gift_service.create_category(CategoryCreate(name="Home"))
    result = await gift_service.list_categories()
    names = [r.name for r in result]
    assert "Sports" in names
    assert "Home" in names


# ---------------------------------------------------------------------------
# GiftService
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_gift_success(gift_service, category):
    payload = GiftCreate(
        title="Wireless Mouse",
        description="Ergonomic mouse",
        category_id=category.id,
        price=29.99,
        occasion="Birthday",
        relationship="Colleague",
    )
    result = await gift_service.create_gift(payload)
    assert result.title == "Wireless Mouse"
    assert result.price == 29.99
    assert result.id is not None


@pytest.mark.asyncio
async def test_create_gift_invalid_category_raises_404(gift_service):
    payload = GiftCreate(
        title="Ghost Gift",
        description="No category",
        category_id=9999,
        price=10.0,
    )
    with pytest.raises(HTTPException) as exc_info:
        await gift_service.create_gift(payload)
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_get_gift_success(gift_service, category):
    created = await gift_service.create_gift(
        GiftCreate(title="Keychain", category_id=category.id, price=9.99)
    )
    result = await gift_service.get_gift(created.id)
    assert result.title == "Keychain"


@pytest.mark.asyncio
async def test_get_gift_not_found_raises_404(gift_service):
    with pytest.raises(HTTPException) as exc_info:
        await gift_service.get_gift(999999)
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_list_gifts_returns_all(gift_service, category):
    await gift_service.create_gift(
        GiftCreate(title="Gift A", category_id=category.id, price=10.0)
    )
    await gift_service.create_gift(
        GiftCreate(title="Gift B", category_id=category.id, price=20.0)
    )
    params = GiftFilterParams()
    result = await gift_service.list_gifts(params)
    assert len(result) >= 2


@pytest.mark.asyncio
async def test_list_gifts_with_price_filter(gift_service, category):
    await gift_service.create_gift(
        GiftCreate(title="Cheap", category_id=category.id, price=5.0)
    )
    await gift_service.create_gift(
        GiftCreate(title="Expensive", category_id=category.id, price=200.0)
    )
    params = GiftFilterParams(max_price=50.0)
    result = await gift_service.list_gifts(params)
    assert all(g.price <= 50.0 for g in result)


@pytest.mark.asyncio
async def test_list_gifts_with_occasion_filter(gift_service, category):
    await gift_service.create_gift(
        GiftCreate(title="Birthday Gift", category_id=category.id, price=30.0, occasion="Birthday")
    )
    await gift_service.create_gift(
        GiftCreate(title="Wedding Gift", category_id=category.id, price=50.0, occasion="Wedding")
    )
    params = GiftFilterParams(occasion="Birthday")
    result = await gift_service.list_gifts(params)
    assert all(g.occasion == "Birthday" for g in result)


@pytest.mark.asyncio
async def test_update_gift_success(gift_service, category):
    created = await gift_service.create_gift(
        GiftCreate(title="Old Title", category_id=category.id, price=15.0)
    )
    updated = await gift_service.update_gift(
        created.id, GiftUpdate(title="New Title", price=25.0)
    )
    assert updated.title == "New Title"
    assert updated.price == 25.0


@pytest.mark.asyncio
async def test_update_gift_not_found_raises_404(gift_service):
    with pytest.raises(HTTPException) as exc_info:
        await gift_service.update_gift(999999, GiftUpdate(title="X"))
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_update_gift_invalid_category_raises_404(gift_service, category):
    created = await gift_service.create_gift(
        GiftCreate(title="Test", category_id=category.id, price=10.0)
    )
    with pytest.raises(HTTPException) as exc_info:
        await gift_service.update_gift(created.id, GiftUpdate(category_id=99999))
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_gift_success(gift_service, category):
    created = await gift_service.create_gift(
        GiftCreate(title="To Delete", category_id=category.id, price=5.0)
    )
    # Should not raise
    await gift_service.delete_gift(created.id)

    with pytest.raises(HTTPException) as exc_info:
        await gift_service.get_gift(created.id)
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_gift_not_found_raises_404(gift_service):
    with pytest.raises(HTTPException) as exc_info:
        await gift_service.delete_gift(999999)
    assert exc_info.value.status_code == 404
