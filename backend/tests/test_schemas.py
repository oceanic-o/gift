"""
Unit Tests: Pydantic Schema Validation
"""
import pytest
from pydantic import ValidationError
from app.schemas.user import UserCreate
from app.schemas.gift import GiftCreate, GiftFilterParams
from app.schemas.recommendation import InteractionCreate, RAGQueryCreate
from app.models.models import InteractionType


def test_user_create_valid():
    user = UserCreate(name="Alice Smith", email="alice@example.com", password="Password123!")
    assert user.name == "Alice Smith"
    assert user.email == "alice@example.com"


def test_user_create_short_password():
    with pytest.raises(ValidationError, match="at least 8"):
        UserCreate(name="Bob", email="bob@test.com", password="short")


def test_user_create_invalid_email():
    with pytest.raises(ValidationError):
        UserCreate(name="Carol", email="not-an-email", password="ValidPassword1!")


def test_user_create_empty_name():
    with pytest.raises(ValidationError, match="cannot be empty"):
        UserCreate(name="   ", email="test@test.com", password="ValidPassword1!")


def test_gift_create_valid():
    gift = GiftCreate(
        title="Leather Wallet",
        description="Premium wallet",
        category_id=1,
        price=49.99,
        occasion="Birthday",
        relationship="Friend",
    )
    assert gift.title == "Leather Wallet"
    assert gift.price == 49.99


def test_gift_create_negative_price():
    with pytest.raises(ValidationError, match="Price cannot be negative"):
        GiftCreate(title="Test Gift", category_id=1, price=-10.0)


def test_gift_create_empty_title():
    with pytest.raises(ValidationError, match="cannot be empty"):
        GiftCreate(title="   ", category_id=1, price=10.0)


def test_interaction_create_valid_rating():
    interaction = InteractionCreate(
        gift_id=1,
        interaction_type=InteractionType.rating,
        rating=4.5,
    )
    assert interaction.rating == 4.5


def test_interaction_create_rating_out_of_range():
    with pytest.raises(ValidationError, match="between 1.0 and 5.0"):
        InteractionCreate(
            gift_id=1,
            interaction_type=InteractionType.rating,
            rating=6.0,
        )


def test_rag_query_create_valid():
    query = RAGQueryCreate(query="What is a good birthday gift for my mom?")
    assert query.query.startswith("What")


def test_rag_query_create_too_short():
    with pytest.raises(ValidationError, match="at least 3 characters"):
        RAGQueryCreate(query="Hi")


def test_rag_query_create_too_long():
    with pytest.raises(ValidationError, match="1000 characters"):
        RAGQueryCreate(query="x" * 1001)


def test_gift_filter_params_defaults():
    params = GiftFilterParams()
    assert params.skip == 0
    assert params.limit == 20
    assert params.occasion is None
