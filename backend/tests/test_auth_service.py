import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from app.schemas.auth import SignupRequest, LoginRequest


@pytest.fixture
def mock_session():
    return AsyncMock()


@pytest.fixture
def mock_user():
    user = MagicMock()
    user.id = "new-user-id"
    user.name = "Priya Singh"
    user.email = "priya.singh@college.edu"
    user.password_hash = "hashed-password"
    user.role = "student"
    user.status = "active"
    return user


@pytest.mark.asyncio
class TestSignup:
    async def test_creates_student_and_returns_tokens(self, mock_session, mock_user):
        mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: None))
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        with (
            patch("app.services.auth.hash_password", return_value="hashed-password"),
            patch("app.services.auth.create_access_token", return_value="access-token"),
            patch("app.services.auth.create_refresh_token", return_value="refresh-token"),
        ):
            from app.services.auth import signup

            result = await signup(
                db=mock_session,
                data=SignupRequest(
                    name="Priya Singh",
                    email="priya.singh@college.edu",
                    password="SecurePass123",
                    role="student",
                ),
            )

        assert mock_session.add.called
        assert mock_session.commit.called
        assert result["user"]["name"] == "Priya Singh"
        assert result["user"]["role"] == "student"
        assert result["user"]["status"] == "active"
        assert "password_hash" not in result["user"]
        assert result["accessToken"] == "access-token"
        assert result["refreshToken"] == "refresh-token"

    async def test_creates_teacher_with_pending_status(self, mock_session, mock_user):
        mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: None))
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        with (
            patch("app.services.auth.hash_password", return_value="hashed-password"),
            patch("app.services.auth.create_access_token", return_value="access-token"),
            patch("app.services.auth.create_refresh_token", return_value="refresh-token"),
        ):
            from app.services.auth import signup

            result = await signup(
                db=mock_session,
                data=SignupRequest(
                    name="Dr. Rajesh",
                    email="rajesh@college.edu",
                    password="SecurePass123",
                    role="teacher",
                ),
            )

        assert result["user"]["role"] == "teacher"
        assert result["user"]["status"] == "pending"

    async def test_raises_on_duplicate_email(self, mock_session):
        mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: MagicMock()))

        from app.services.auth import signup

        with pytest.raises(Exception) as exc:
            await signup(
                db=mock_session,
                data=SignupRequest(
                    name="Priya Singh",
                    email="priya.singh@college.edu",
                    password="SecurePass123",
                    role="student",
                ),
            )
        assert "already" in str(exc.value).lower() or "409" in str(exc.value)


@pytest.mark.asyncio
class TestLogin:
    async def test_returns_tokens_on_valid_credentials(self, mock_session, mock_user):
        mock_user.status = "active"
        mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: mock_user))

        with (
            patch("app.services.auth.verify_password", return_value=True),
            patch("app.services.auth.create_access_token", return_value="access-token"),
            patch("app.services.auth.create_refresh_token", return_value="refresh-token"),
        ):
            from app.services.auth import login

            result = await login(
                db=mock_session,
                email="priya.singh@college.edu",
                password="SecurePass123",
            )

        assert result["user"]["email"] == "priya.singh@college.edu"
        assert result["accessToken"] == "access-token"
        assert result["refreshToken"] == "refresh-token"

    async def test_raises_on_wrong_password(self, mock_session, mock_user):
        mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: mock_user))

        with patch("app.services.auth.verify_password", return_value=False):
            from app.services.auth import login

            with pytest.raises(Exception) as exc:
                await login(
                    db=mock_session,
                    email="priya.singh@college.edu",
                    password="wrong-password",
                )
            assert "Invalid" in str(exc.value)

    async def test_raises_on_user_not_found(self, mock_session):
        mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: None))

        from app.services.auth import login

        with pytest.raises(Exception) as exc:
            await login(
                db=mock_session,
                email="nonexistent@college.edu",
                password="SecurePass123",
            )
        assert "not found" in str(exc.value).lower()

    async def test_raises_on_inactive_user(self, mock_session, mock_user):
        mock_user.status = "pending"
        mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: mock_user))

        with patch("app.services.auth.verify_password", return_value=True):
            from app.services.auth import login

            with pytest.raises(Exception) as exc:
                await login(
                    db=mock_session,
                    email="priya.singh@college.edu",
                    password="SecurePass123",
                )
            assert "not active" in str(exc.value).lower()


@pytest.mark.asyncio
class TestRefresh:
    async def test_returns_new_tokens(self):
        from app.models.user import User

        user = User(id=uuid.uuid4(), name="Test", email="test@test.com")
        user.role = "admin"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        payload = {"sub": str(user.id), "type": "refresh"}

        with (
            patch("app.services.auth.verify_token", return_value=payload),
            patch("app.services.auth.create_access_token", return_value="new-access-token"),
            patch("app.services.auth.create_refresh_token", return_value="new-refresh-token"),
        ):
            from app.services.auth import refresh

            result = await refresh(db=mock_db, refresh_token="old-refresh-token")

        assert result["accessToken"] == "new-access-token"
        assert result["refreshToken"] == "new-refresh-token"

    async def test_raises_on_wrong_token_type(self):
        from app.models.user import User
        from fastapi import HTTPException

        user = User(id=uuid.uuid4(), name="Test", email="test@test.com")
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        payload = {"sub": str(user.id), "type": "access"}

        with patch("app.services.auth.verify_token", return_value=payload):
            from app.services.auth import refresh

            with pytest.raises(HTTPException) as exc:
                await refresh(db=mock_db, refresh_token="old-token")
            assert exc.value.status_code == 401
            assert "Invalid token type" in str(exc.value.detail)

    async def test_raises_on_blacklisted_token(self):
        from app.models.user import User
        from app.services.auth import refresh, _blacklisted_tokens_fallback, _add_to_blacklist

        _blacklisted_tokens_fallback.clear()

        user = User(id=uuid.uuid4(), name="Test", email="test@test.com")
        mock_db = AsyncMock()
        mock_db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=user))

        payload = {"sub": str(user.id), "type": "refresh"}
        await _add_to_blacklist("revoked-token", 3600)

        with patch("app.services.auth.verify_token", return_value=payload):
            from app.services.auth import refresh

            with pytest.raises(Exception) as exc:
                await refresh(db=mock_db, refresh_token="revoked-token")
            assert "revoked" in str(exc.value).lower()

    async def test_raises_on_user_not_found(self):
        from app.services.auth import refresh

        mock_db = AsyncMock()
        mock_db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=None))

        payload = {"sub": "550e8400-e29b-41d4-a716-446655440000", "type": "refresh"}

        with patch("app.services.auth.verify_token", return_value=payload):
            with pytest.raises(Exception) as exc:
                await refresh(db=mock_db, refresh_token="valid-token")
            assert "not found" in str(exc.value).lower()


@pytest.mark.asyncio
class TestLogout:
    async def test_blacklists_token(self):
        from unittest.mock import patch, AsyncMock
        from app.services.auth import logout, _blacklisted_tokens_fallback

        _blacklisted_tokens_fallback.clear()
        await logout(refresh_token="token-to-blacklist")
        assert "token-to-blacklist" in _blacklisted_tokens_fallback


@pytest.mark.asyncio
class TestGetMe:
    async def test_returns_user_when_found(self):
        from unittest.mock import AsyncMock, MagicMock
        from app.services.auth import get_me
        from datetime import datetime

        mock_user = MagicMock()
        mock_user.id = "550e8400-e29b-41d4-a716-446655440000"
        mock_user.name = "Priya Singh"
        mock_user.email = "priya@college.edu"
        mock_user.role = "student"
        mock_user.status = "active"
        mock_user.created_at = datetime(2026, 1, 1, 0, 0, 0)
        mock_user.updated_at = datetime(2026, 1, 2, 0, 0, 0)

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute.return_value = mock_result

        result = await get_me(db=mock_session, user_id="550e8400-e29b-41d4-a716-446655440000")

        assert result["id"] == "550e8400-e29b-41d4-a716-446655440000"
        assert result["name"] == "Priya Singh"
        assert result["role"] == "student"
        assert result["status"] == "active"
        assert result["created_at"] == "2026-01-01T00:00:00"
        assert result["updated_at"] == "2026-01-02T00:00:00"

    async def test_raises_value_error_on_invalid_uuid(self):
        from app.services.auth import get_me
        from unittest.mock import AsyncMock

        with pytest.raises(ValueError, match="badly formed hexadecimal UUID string"):
            await get_me(db=AsyncMock(), user_id="not-a-uuid")

    async def test_raises_404_when_user_not_found(self):
        from unittest.mock import AsyncMock, MagicMock
        from app.services.auth import get_me

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        with pytest.raises(Exception) as exc:
            await get_me(db=mock_session, user_id="550e8400-e29b-41d4-a716-446655440000")

        assert "not found" in str(exc.value).lower()
