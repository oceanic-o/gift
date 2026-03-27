"""
Unit tests for services/auth_service.py (currently ~48% coverage).
Uses in-memory SQLite via the db_session fixture from conftest.py.
"""
import pytest
from fastapi import HTTPException

from app.services.auth_service import AuthService
from app.schemas.user import UserCreate, UserLogin
from app.models.models import User, UserRole
from app.core.security import hash_password


@pytest.fixture
async def auth_service(db_session):
    return AuthService(db_session)


@pytest.fixture
async def existing_user(db_session):
    """Insert a user directly for login tests."""
    user = User(
        name="Existing User",
        email="existing@example.com",
        password_hash=hash_password("CorrectPass123!"),
        role=UserRole.user,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


# ---------------------------------------------------------------------------
# register
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_register_new_user_success(auth_service):
    payload = UserCreate(
        name="Alice",
        email="alice@example.com",
        password="SecurePass123!",
    )
    result = await auth_service.register(payload)
    assert result.email == "alice@example.com"
    assert result.name == "Alice"
    assert result.id is not None


@pytest.mark.asyncio
async def test_register_lowercases_email(auth_service):
    payload = UserCreate(
        name="Bob",
        email="BOB@EXAMPLE.COM",
        password="SecurePass123!",
    )
    result = await auth_service.register(payload)
    assert result.email == "bob@example.com"


@pytest.mark.asyncio
async def test_register_duplicate_email_raises_409(auth_service, existing_user):
    payload = UserCreate(
        name="Duplicate",
        email="existing@example.com",
        password="AnotherPass123!",
    )
    with pytest.raises(HTTPException) as exc_info:
        await auth_service.register(payload)
    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_register_default_role_is_user(auth_service):
    payload = UserCreate(
        name="Charlie",
        email="charlie@example.com",
        password="SecurePass123!",
    )
    result = await auth_service.register(payload)
    assert result.role == UserRole.user


# ---------------------------------------------------------------------------
# login
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_success(auth_service, existing_user):
    payload = UserLogin(email="existing@example.com", password="CorrectPass123!")
    result = await auth_service.login(payload)
    assert result.access_token is not None
    assert result.user.email == "existing@example.com"


@pytest.mark.asyncio
async def test_login_wrong_password_raises_401(auth_service, existing_user):
    payload = UserLogin(email="existing@example.com", password="WrongPassword!")
    with pytest.raises(HTTPException) as exc_info:
        await auth_service.login(payload)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_email_raises_401(auth_service):
    payload = UserLogin(email="nobody@example.com", password="SomePass123!")
    with pytest.raises(HTTPException) as exc_info:
        await auth_service.login(payload)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_login_case_insensitive_email(auth_service, existing_user):
    payload = UserLogin(email="EXISTING@EXAMPLE.COM", password="CorrectPass123!")
    result = await auth_service.login(payload)
    assert result.access_token is not None
