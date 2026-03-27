"""
Unit Tests: Security (JWT + Password Hashing)
"""
import pytest
from datetime import timedelta
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)
from fastapi import HTTPException


def test_hash_password_is_not_plaintext():
    """Hashed password should not equal the original."""
    password = "SecurePassword123!"
    hashed = hash_password(password)
    assert hashed != password
    assert len(hashed) > 20


def test_verify_password_correct():
    """Correct password should verify successfully."""
    password = "TestPassword456!"
    hashed = hash_password(password)
    assert verify_password(password, hashed) is True


def test_verify_password_wrong():
    """Wrong password should fail verification."""
    hashed = hash_password("CorrectPassword!")
    assert verify_password("WrongPassword!", hashed) is False


def test_create_and_decode_access_token():
    """Created token should be decodable with correct payload."""
    data = {"sub": "42", "role": "user"}
    token = create_access_token(data, expires_delta=timedelta(minutes=30))

    decoded = decode_access_token(token)
    assert decoded["sub"] == "42"
    assert decoded["role"] == "user"


def test_decode_invalid_token():
    """Invalid token should raise HTTPException 401."""
    with pytest.raises(HTTPException) as exc_info:
        decode_access_token("this.is.not.a.valid.token")
    assert exc_info.value.status_code == 401


def test_token_expiry():
    """Token with negative expiry should be rejected."""
    data = {"sub": "1"}
    token = create_access_token(data, expires_delta=timedelta(seconds=-1))
    with pytest.raises(HTTPException) as exc_info:
        decode_access_token(token)
    assert exc_info.value.status_code == 401
