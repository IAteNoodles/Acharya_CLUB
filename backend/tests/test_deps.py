import pytest
from fastapi import Depends, FastAPI, HTTPException
from httpx import AsyncClient, ASGITransport
from app.core.security import create_access_token, create_refresh_token


@pytest.fixture
def app():
    from app.api.deps import get_current_user, require_admin, require_teacher_or_admin

    test_app = FastAPI()

    @test_app.get("/api/v1/protected")
    async def protected(current_user: dict = Depends(get_current_user)):
        return {"userId": current_user["sub"], "role": current_user["role"]}

    @test_app.get("/api/v1/admin")
    async def admin_only(current_user: dict = Depends(require_admin)):
        return {"message": "admin access granted"}

    @test_app.get("/api/v1/faculty")
    async def faculty_only(current_user: dict = Depends(require_teacher_or_admin)):
        return {"message": "faculty access granted"}

    return test_app


@pytest.mark.asyncio
class TestGetCurrentUser:
    async def test_returns_401_when_no_auth_header(self, app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            res = await ac.get("/api/v1/protected")
        assert res.status_code == 401

    async def test_returns_401_when_not_bearer(self, app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            res = await ac.get("/api/v1/protected", headers={"Authorization": "Basic token"})
        assert res.status_code == 401

    async def test_returns_401_when_token_invalid(self, app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            res = await ac.get("/api/v1/protected", headers={"Authorization": "Bearer invalid"})
        assert res.status_code == 401

    async def test_returns_user_when_token_valid(self, app):
        token = create_access_token(user_id="test-user-id", role="student")
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            res = await ac.get("/api/v1/protected", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        data = res.json()
        assert data["userId"] == "test-user-id"
        assert data["role"] == "student"

    async def test_rejects_refresh_token(self, app):
        token = create_refresh_token(user_id="test-user-id")
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            res = await ac.get("/api/v1/protected", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 401


@pytest.mark.asyncio
class TestRequireAdmin:
    async def test_allows_admin(self, app):
        token = create_access_token(user_id="admin-id", role="admin")
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            res = await ac.get("/api/v1/admin", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        assert res.json()["message"] == "admin access granted"

    async def test_rejects_student(self, app):
        token = create_access_token(user_id="student-id", role="student")
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            res = await ac.get("/api/v1/admin", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 403


@pytest.mark.asyncio
class TestRequireTeacherOrAdmin:
    async def test_allows_teacher(self, app):
        token = create_access_token(user_id="teacher-id", role="teacher")
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            res = await ac.get("/api/v1/faculty", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        assert res.json()["message"] == "faculty access granted"

    async def test_allows_admin(self, app):
        token = create_access_token(user_id="admin-id", role="admin")
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            res = await ac.get("/api/v1/faculty", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200

    async def test_rejects_student(self, app):
        token = create_access_token(user_id="student-id", role="student")
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            res = await ac.get("/api/v1/faculty", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 403

    async def test_returns_401_when_no_user(self, app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            res = await ac.get("/api/v1/admin")
        assert res.status_code == 401
