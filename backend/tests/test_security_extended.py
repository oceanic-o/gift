"""
Unit tests for core/security.py — covering decode_access_token, get_current_user,
get_current_admin, and edge cases not covered by test_security.py.
"""
import pytest
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException

from app.core.security import (
    decode_access_token,
    create_access_token,
    get_current_user,
    get_current_admin,
)


# ---------------------------------------------------------------------------
# decode_access_token
# ---------------------------------------------------------------------------

def test_decode_valid_token():
    token = create_access_token({"sub": "42", "role": "user"})
    payload = decode_access_token(token)
    assert payload["sub"] == "42"
    assert payload["role"] == "user"


def test_decode_expired_token():
    token = create_access_token(
        {"sub": "1"}, expires_delta=timedelta(seconds=-1)
    )
    with pytest.raises(HTTPException) as exc_info:
        decode_access_token(token)
    assert exc_info.value.status_code == 401


def test_decode_invalid_token():
    with pytest.raises(HTTPException) as exc_info:
        decode_access_token("not.a.valid.token")
    assert exc_info.value.status_code == 401


def test_decode_tampered_token():
    token = create_access_token({"sub": "1"})
    tampered = token[:-5] + "XXXXX"
    with pytest.raises(HTTPException) as exc_info:
        decode_access_token(tampered)
    assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# get_current_user — async, using mocks
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_current_user_success():
    token = create_access_token({"sub": "7", "role": "user"})
    mock_credentials = MagicMock()
    mock_credentials.credentials = token

    mock_user = MagicMock()
    mock_user.id = 7
    mock_repo = AsyncMock()
    mock_repo.get_by_id.return_value = mock_user

    mock_db = AsyncMock()

    with patch("app.repositories.user_repository.UserRepository", return_value=mock_repo):
        user = await get_current_user(credentials=mock_credentials, db=mock_db)

    assert user.id == 7
    mock_repo.get_by_id.assert_called_once_with(7)


@pytest.mark.asyncio
async def test_get_current_user_user_not_found():
    token = create_access_token({"sub": "99", "role": "user"})
    mock_credentials = MagicMock()
    mock_credentials.credentials = token

    mock_repo = AsyncMock()
    mock_repo.get_by_id.return_value = None
    mock_db = AsyncMock()

    with patch("app.repositories.user_repository.UserRepository", return_value=mock_repo):
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials=mock_credentials, db=mock_db)

    assert exc_info.value.status_code == 401
    assert "not found" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_get_current_user_missing_sub_claim():
    # Token without 'sub'
    token = create_access_token({"role": "user"})
    mock_credentials = MagicMock()
    mock_credentials.credentials = token
    mock_db = AsyncMock()

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(credentials=mock_credentials, db=mock_db)

    assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# get_current_admin
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_current_admin_success():
    from app.models.models import UserRole
    mock_user = MagicMock()
    mock_user.role = UserRole.admin
    result = await get_current_admin(current_user=mock_user)
    assert result is mock_user


@pytest.mark.asyncio
async def test_get_current_admin_forbidden_for_regular_user():
    from app.models.models import UserRole
    mock_user = MagicMock()
    mock_user.role = UserRole.user
    with pytest.raises(HTTPException) as exc_info:
        await get_current_admin(current_user=mock_user)
    assert exc_info.value.status_code == 403
