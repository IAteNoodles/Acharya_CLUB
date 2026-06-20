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
