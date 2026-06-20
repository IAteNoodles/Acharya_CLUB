import pytest
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


@pytest.mark.asyncio
class TestRefresh:
    async def test_returns_new_tokens(self):
        payload = {"sub": "user-id", "type": "refresh"}

        with (
            patch("app.services.auth.verify_token", return_value=payload),
            patch("app.services.auth.create_access_token", return_value="new-access-token"),
            patch("app.services.auth.create_refresh_token", return_value="new-refresh-token"),
        ):
            from app.services.auth import refresh

            result = await refresh(refresh_token="old-refresh-token")

        assert result["accessToken"] == "new-access-token"
        assert result["refreshToken"] == "new-refresh-token"


@pytest.mark.asyncio
class TestLogout:
    async def test_blacklists_token(self):
        from app.services.auth import logout, _blacklisted_tokens

        await logout(refresh_token="token-to-blacklist")
        assert "token-to-blacklist" in _blacklisted_tokens
