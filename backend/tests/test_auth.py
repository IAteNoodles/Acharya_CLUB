import pytest
from httpx import AsyncClient, ASGITransport


@pytest.mark.asyncio
class TestAuthValidation:
    """Tests that validate API error handling without database."""

    async def test_signup_validation_name_too_short(self, app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.post(
                "/api/v1/auth/signup",
                json={
                    "name": "A",
                    "email": "test@college.edu",
                    "password": "SecurePass123",
                    "role": "student",
                },
            )
        assert res.status_code == 422

    async def test_signup_validation_invalid_email(self, app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.post(
                "/api/v1/auth/signup",
                json={
                    "name": "Test User",
                    "email": "not-an-email",
                    "password": "SecurePass123",
                    "role": "student",
                },
            )
        assert res.status_code == 422

    async def test_signup_validation_wrong_domain(self, app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.post(
                "/api/v1/auth/signup",
                json={
                    "name": "Test User",
                    "email": "test@gmail.com",
                    "password": "SecurePass123",
                    "role": "student",
                },
            )
        assert res.status_code == 422

    async def test_signup_validation_password_too_short(self, app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.post(
                "/api/v1/auth/signup",
                json={
                    "name": "Test User",
                    "email": "test@college.edu",
                    "password": "short",
                    "role": "student",
                },
            )
        assert res.status_code == 422

    async def test_signup_validation_invalid_role(self, app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.post(
                "/api/v1/auth/signup",
                json={
                    "name": "Test User",
                    "email": "test@college.edu",
                    "password": "SecurePass123",
                    "role": "admin",
                },
            )
        assert res.status_code == 422

    async def test_login_validation_empty_email(self, app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.post(
                "/api/v1/auth/login",
                json={"email": "", "password": "SecurePass123"},
            )
        assert res.status_code == 422

    async def test_change_password_unauthenticated(self, app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.post(
                "/api/v1/auth/change-password",
                json={"currentPassword": "OldPass123", "newPassword": "NewPass456"},
            )
        assert res.status_code == 401

    async def test_change_password_validation_short_new_password(self, app):
        from app.core.security import create_access_token

        token = create_access_token(user_id="550e8400-e29b-41d4-a716-446655440000", role="student")
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.post(
                "/api/v1/auth/change-password",
                headers={"Authorization": f"Bearer {token}"},
                json={"currentPassword": "OldPass123", "newPassword": "short"},
            )
        assert res.status_code == 422

    async def test_change_password_success(self, app):
        from unittest.mock import AsyncMock, patch
        from app.core.security import create_access_token

        token = create_access_token(user_id="550e8400-e29b-41d4-a716-446655440000", role="student")
        with patch(
            "app.services.auth.change_password",
            new=AsyncMock(return_value={"message": "Password changed successfully"}),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                res = await client.post(
                    "/api/v1/auth/change-password",
                    headers={"Authorization": f"Bearer {token}"},
                    json={"currentPassword": "OldPass123", "newPassword": "NewPass456"},
                )
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["data"]["message"] == "Password changed successfully"

    async def test_me_unauthenticated(self, app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get("/api/v1/auth/me")
        assert res.status_code == 401

    async def test_logout_unauthenticated(self, app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.post(
                "/api/v1/auth/logout",
                json={"refreshToken": "some-token"},
            )
        assert res.status_code == 401

    async def test_refresh_invalid_token(self, app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.post(
                "/api/v1/auth/refresh",
                json={"refreshToken": "invalid-token"},
            )
        assert res.status_code == 401

    async def test_health_check_unaffected(self, app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get("/api/v1/health")
        assert res.status_code == 200
        assert res.json()["data"]["status"] == "ok"


@pytest.mark.asyncio
class TestAuthAPI:
    """Tests that exercise the auth router response formatting paths."""

    @pytest.fixture
    def api_app(self):
        from fastapi import FastAPI
        from app.api.v1.auth import router
        from app.api import deps
        from app.core.exceptions import register_exception_handlers

        app = FastAPI()
        app.include_router(router)
        register_exception_handlers(app)

        async def mock_user():
            return {"sub": "550e8400-e29b-41d4-a716-446655440000", "role": "student"}

        app.dependency_overrides[deps.get_current_user] = mock_user
        return app

    async def test_signup_returns_201_with_response_shape(self, api_app):
        from unittest.mock import patch

        mock_result = {
            "user": {"id": "u1", "name": "Test", "email": "test@college.edu", "role": "student", "status": "active"},
            "accessToken": "access-token",
            "refreshToken": "refresh-token",
        }
        with patch("app.services.auth.signup", return_value=mock_result):
            transport = ASGITransport(app=api_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                res = await client.post(
                    "/api/v1/auth/signup",
                    json={"name": "Test User", "email": "test@college.edu", "password": "SecurePass123", "role": "student"},
                )

        assert res.status_code == 201
        data = res.json()
        assert data["success"] is True
        assert data["data"]["user"]["name"] == "Test"
        assert data["data"]["accessToken"] == "access-token"

    async def test_login_returns_200_with_response_shape(self, api_app):
        from unittest.mock import patch

        mock_result = {
            "user": {"id": "u1", "name": "Test", "email": "test@college.edu", "role": "student", "status": "active"},
            "accessToken": "access-token",
            "refreshToken": "refresh-token",
        }
        with patch("app.services.auth.login", return_value=mock_result):
            transport = ASGITransport(app=api_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                res = await client.post(
                    "/api/v1/auth/login",
                    json={"email": "test@college.edu", "password": "SecurePass123"},
                )

        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert "accessToken" in data["data"]

    async def test_refresh_returns_200_with_response_shape(self, api_app):
        from unittest.mock import patch

        mock_result = {"accessToken": "new-access", "refreshToken": "new-refresh"}
        with patch("app.services.auth.refresh", return_value=mock_result):
            transport = ASGITransport(app=api_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                res = await client.post(
                    "/api/v1/auth/refresh",
                    json={"refreshToken": "valid-refresh-token"},
                )

        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True

    async def test_logout_returns_200(self, api_app):
        from unittest.mock import patch

        with patch("app.services.auth.logout", return_value={"message": "Logged out successfully"}):
            transport = ASGITransport(app=api_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                res = await client.post(
                    "/api/v1/auth/logout",
                    json={"refreshToken": "any-token"},
                )

        assert res.status_code == 200
        assert res.json()["success"] is True

    async def test_me_returns_200(self, api_app):
        from unittest.mock import patch

        mock_user_data = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "name": "Test User",
            "email": "test@college.edu",
            "role": "student",
            "status": "active",
            "created_at": "2026-01-01T00:00:00",
            "updated_at": "2026-01-02T00:00:00",
        }
        with patch("app.services.auth.get_me", return_value=mock_user_data):
            transport = ASGITransport(app=api_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                res = await client.get("/api/v1/auth/me")

        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["data"]["user"]["name"] == "Test User"
