from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
    verify_token,
)


class TestCreateAccessToken:
    def test_returns_valid_jwt_string(self):
        token = create_access_token(user_id="user-1", role="student")
        assert token is not None
        assert isinstance(token, str)
        assert len(token.split(".")) == 3

    def test_contains_correct_payload(self):
        token = create_access_token(user_id="user-1", role="student")
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        assert payload["sub"] == "user-1"
        assert payload["role"] == "student"
        assert payload["type"] == "access"
        assert "exp" in payload
        assert "iat" in payload

    def test_expires_in_15_minutes(self):
        token = create_access_token(user_id="user-1", role="student")
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        iat = datetime.fromtimestamp(payload["iat"], tz=timezone.utc)
        diff = exp - iat
        assert diff.total_seconds() == pytest.approx(900, abs=5), "Expected ~15 min expiry"


class TestCreateRefreshToken:
    def test_returns_valid_jwt_string(self):
        token = create_refresh_token(user_id="user-1")
        assert token is not None
        assert isinstance(token, str)
        assert len(token.split(".")) == 3

    def test_contains_correct_payload(self):
        token = create_refresh_token(user_id="user-1")
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        assert payload["sub"] == "user-1"
        assert payload["type"] == "refresh"
        assert "role" not in payload

    def test_expires_in_7_days(self):
        token = create_refresh_token(user_id="user-1")
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        iat = datetime.fromtimestamp(payload["iat"], tz=timezone.utc)
        diff = exp - iat
        assert diff.total_seconds() == pytest.approx(604800, abs=60), "Expected ~7 day expiry"


class TestVerifyToken:
    def test_decodes_valid_access_token(self):
        token = create_access_token(user_id="user-1", role="student")
        payload = verify_token(token)
        assert payload["sub"] == "user-1"
        assert payload["role"] == "student"
        assert payload["type"] == "access"

    def test_decodes_valid_refresh_token(self):
        token = create_refresh_token(user_id="user-1")
        payload = verify_token(token)
        assert payload["sub"] == "user-1"
        assert payload["type"] == "refresh"

    def test_raises_on_invalid_token(self):
        with pytest.raises(Exception):
            verify_token("invalid-token")

    def test_raises_on_expired_token(self):
        token = create_access_token(user_id="user-1", role="student", expires_delta=timedelta(seconds=-1))
        with pytest.raises(Exception):
            verify_token(token)

    def test_raises_on_wrong_secret(self):
        from jose import jwt as jose_jwt
        token = jose_jwt.encode({"sub": "user-1"}, "different-secret", algorithm="HS256")
        with pytest.raises(Exception):
            verify_token(token)


class TestPasswordHashing:
    def test_hash_returns_different_string(self):
        hashed = hash_password("SecurePass123")
        assert hashed != "SecurePass123"
        assert isinstance(hashed, str)

    def test_verify_correct_password_returns_true(self):
        hashed = hash_password("SecurePass123")
        assert verify_password("SecurePass123", hashed) is True

    def test_verify_wrong_password_returns_false(self):
        hashed = hash_password("SecurePass123")
        assert verify_password("WrongPassword", hashed) is False

    def test_same_password_produces_different_hashes(self):
        hash1 = hash_password("SecurePass123")
        hash2 = hash_password("SecurePass123")
        assert hash1 != hash2
