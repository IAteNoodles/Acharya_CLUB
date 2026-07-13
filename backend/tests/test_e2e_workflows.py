"""
End-to-end workflow tests using real PostgreSQL and Redis via testcontainers.
Tests complete user journeys through the full application stack.
"""

import asyncio
import os
import sys
import importlib
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

# Windows fix: asyncpg requires SelectorEventLoop (not ProactorEventLoop)
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

pytestmark = [
    pytest.mark.asyncio(loop_scope="session"),
    pytest.mark.e2e,
]


CONTAINER_IMAGE_POSTGRES = "postgres:16-alpine"
CONTAINER_IMAGE_REDIS = "redis:7-alpine"


@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer(CONTAINER_IMAGE_POSTGRES) as pg:
        yield pg


@pytest.fixture(scope="session")
def redis_container():
    with RedisContainer(CONTAINER_IMAGE_REDIS) as r:
        yield r


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def e2e_client(postgres_container, redis_container):
    db_url = postgres_container.get_connection_url(driver="asyncpg")
    redis_host = redis_container.get_container_host_ip()
    redis_port = redis_container.get_exposed_port(6379)
    redis_url = f"redis://{redis_host}:{redis_port}/0"

    # Save original env vars for cleanup
    _saved = {k: os.environ.get(k) for k in ("DATABASE_URL", "REDIS_URL", "JWT_SECRET", "ENVIRONMENT", "DEBUG", "CORS_ORIGINS", "ASYNC_NULLPOOL")}

    os.environ["DATABASE_URL"] = db_url
    os.environ["REDIS_URL"] = redis_url
    os.environ["JWT_SECRET"] = "e2e-test-jwt-secret-at-least-32-chars"
    os.environ["ENVIRONMENT"] = "test"
    os.environ["DEBUG"] = "false"
    os.environ["CORS_ORIGINS"] = '["http://localhost:5173"]'
    os.environ["ASYNC_NULLPOOL"] = "1"

    # Clean all app modules so they reimport with correct env vars
    for mod_name in list(sys.modules):
        if mod_name.startswith("app.") or mod_name == "app":
            del sys.modules[mod_name]
    importlib.invalidate_caches()

    # Import database module (uses NullPool for test isolation)
    import app.core.database

    # Import models so Base.metadata is populated
    from app.models.base import Base
    import app.models.user  # noqa: F401
    import app.models.event  # noqa: F401
    import app.models.registration  # noqa: F401
    import app.models.attendance  # noqa: F401
    import app.models.notification  # noqa: F401

    # Use sync engine for DB setup
    sync_url = db_url.replace("+asyncpg", "")
    sync_engine = create_engine(sync_url)
    Base.metadata.create_all(sync_engine)

    from app.core.security import hash_password
    from app.models.user import User as UserModel, Role, UserStatus
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    with sync_engine.begin() as conn:
        stmt = pg_insert(UserModel.__table__).values(
            id=uuid.uuid4(),
            name="E2E Admin",
            email="admin@college.edu",
            password_hash=hash_password("AdminPass123"),
            role=Role.ADMIN,
            status=UserStatus.ACTIVE,
        ).on_conflict_do_nothing(index_elements=["email"])
        conn.execute(stmt)
    sync_engine.dispose()

    from app.main import create_app
    app = create_app()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    # Restore env vars so they don't pollute subsequent tests
    for k, v in _saved.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v


class TestE2EWorkflow:

    @pytest.mark.asyncio
    async def test_health_check(self, e2e_client):
        resp = await e2e_client.get("/api/v1/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["status"] == "ok"

    @pytest.mark.asyncio
    async def test_full_event_workflow(self, e2e_client):
        client = e2e_client

        # ── 1. Student signup ──
        resp = await client.post("/api/v1/auth/signup", json={
            "name": "Test Student",
            "email": "student@college.edu",
            "password": "StudentPass123",
            "role": "student",
        })
        assert resp.status_code == 201
        stu_body = resp.json()
        student_id = stu_body["data"]["user"]["id"]
        student_token = stu_body["data"]["accessToken"]
        student_headers = {"Authorization": f"Bearer {student_token}"}

        # Verify student is active
        assert stu_body["data"]["user"]["status"] == "active"

        # ── 2. Teacher signup (starts pending) ──
        resp = await client.post("/api/v1/auth/signup", json={
            "name": "Test Teacher",
            "email": "teacher@college.edu",
            "password": "TeacherPass123",
            "role": "teacher",
        })
        assert resp.status_code == 201
        teacher_body = resp.json()
        teacher_id = teacher_body["data"]["user"]["id"]

        # Verify teacher is pending
        assert teacher_body["data"]["user"]["status"] == "pending"

        # ── 3. Admin login ──
        resp = await client.post("/api/v1/auth/login", json={
            "email": "admin@college.edu",
            "password": "AdminPass123",
        })
        assert resp.status_code == 200
        admin_body = resp.json()
        admin_token = admin_body["data"]["accessToken"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # ── 4. Admin approves teacher ──
        resp = await client.patch(
            f"/api/v1/users/{teacher_id}/approve",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "active"

        # ── 5. Teacher login (now active) ──
        resp = await client.post("/api/v1/auth/login", json={
            "email": "teacher@college.edu",
            "password": "TeacherPass123",
        })
        assert resp.status_code == 200
        teacher_token = resp.json()["data"]["accessToken"]
        teacher_headers = {"Authorization": f"Bearer {teacher_token}"}

        # ── 6. Admin creates event ──
        future = datetime.now(timezone.utc) + timedelta(days=30)
        resp = await client.post("/api/v1/events", json={
            "title": "E2E Test Event",
            "description": "Created during E2E test",
            "event_type": "in_college",
            "category": "participant",
            "venue": "Main Auditorium",
            "start_date": future.isoformat(),
            "end_date": (future + timedelta(hours=4)).isoformat(),
        }, headers=admin_headers)
        assert resp.status_code == 201
        event = resp.json()
        event_id = event["id"]
        assert event["status"] == "draft"

        # ── 7. Admin assigns teacher as coordinator ──
        resp = await client.patch(
            f"/api/v1/events/{event_id}/assign-coordinator",
            json={"coordinator_id": teacher_id},
            headers=admin_headers,
        )
        assert resp.status_code == 200

        # ── 8. Admin approves event ──
        resp = await client.patch(
            f"/api/v1/events/{event_id}/approve",
            json={},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "approved"

        # ── 9. Student registers for event ──
        resp = await client.post("/api/v1/registrations", json={
            "event_id": event_id,
            "role_type": "participant",
        }, headers=student_headers)
        assert resp.status_code == 201
        reg_body = resp.json()
        reg_id = reg_body["data"]["id"]
        assert reg_body["data"]["status"] == "pending"

        # ── 10. Teacher accepts registration ──
        resp = await client.patch(
            f"/api/v1/registrations/{reg_id}/accept",
            headers=teacher_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "accepted"

        # ── 11. Teacher marks attendance ──
        today = datetime.now(timezone.utc).date().isoformat()
        resp = await client.post("/api/v1/attendance/bulk", json={
            "eventId": event_id,
            "date": today,
            "records": [{"studentId": student_id, "present": True}],
        }, headers=teacher_headers)
        assert resp.status_code == 200
        att_body = resp.json()
        assert att_body["data"]["count"] == 1

        # ── 12. Student views own attendance ──
        resp = await client.get("/api/v1/attendance/my", headers=student_headers)
        assert resp.status_code == 200
        assert len(resp.json()["data"]) >= 1

        # ── 13. Teacher views event attendance ──
        resp = await client.get(
            f"/api/v1/attendance/event/{event_id}",
            headers=teacher_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()["data"]) >= 1

        # ── 14. Student notifications ──
        resp = await client.get("/api/v1/notifications", headers=student_headers)
        assert resp.status_code == 200
        notif_list = resp.json()["data"]
        unread_resp = await client.get(
            "/api/v1/notifications/unread-count", headers=student_headers,
        )
        assert unread_resp.status_code == 200
        unread = unread_resp.json()["data"]["count"]

        # Mark all notifications as read
        if unread > 0:
            resp = await client.patch(
                "/api/v1/notifications/read-all", headers=student_headers,
            )
            assert resp.status_code == 200

        # ── 15. Admin dashboard ──
        resp = await client.get("/api/v1/reports/dashboard", headers=admin_headers)
        assert resp.status_code == 200
        dash = resp.json()
        sections = ["users", "events", "registrations", "attendance", "notifications"]
        for s in sections:
            assert s in dash["data"], f"Missing dashboard section: {s}"

    @pytest.mark.asyncio
    async def test_auth_validation_errors(self, e2e_client):
        client = e2e_client

        # Signup with invalid email domain
        resp = await client.post("/api/v1/auth/signup", json={
            "name": "Bad Email",
            "email": "test@gmail.com",
            "password": "StrongPass123",
            "role": "student",
        })
        assert resp.status_code == 422

        # Login with wrong password
        resp = await client.post("/api/v1/auth/login", json={
            "email": "student@college.edu",
            "password": "WrongPassword",
        })
        assert resp.status_code == 401

        # Unauthenticated access
        resp = await client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_permission_enforcement(self, e2e_client):
        client = e2e_client

        # Re-login as student
        resp = await client.post("/api/v1/auth/login", json={
            "email": "student@college.edu",
            "password": "StudentPass123",
        })
        assert resp.status_code == 200
        student_token = resp.json()["data"]["accessToken"]
        student_headers = {"Authorization": f"Bearer {student_token}"}

        # Student cannot access pending teachers
        resp = await client.get(
            "/api/v1/users/pending-teachers", headers=student_headers,
        )
        assert resp.status_code == 403

        # Student cannot access dashboard
        resp = await client.get(
            "/api/v1/reports/dashboard", headers=student_headers,
        )
        assert resp.status_code == 403

        # Student cannot mark attendance
        resp = await client.post("/api/v1/attendance/bulk", json={
            "eventId": "00000000-0000-0000-0000-000000000000",
            "date": "2026-01-01",
            "records": [],
        }, headers=student_headers)
        assert resp.status_code in (403, 422)

    @pytest.mark.asyncio
    async def test_refresh_token_flow(self, e2e_client):
        client = e2e_client

        # Login to get tokens
        resp = await client.post("/api/v1/auth/login", json={
            "email": "student@college.edu",
            "password": "StudentPass123",
        })
        assert resp.status_code == 200
        body = resp.json()
        refresh_token = body["data"]["refreshToken"]

        # Refresh token
        resp = await client.post("/api/v1/auth/refresh", json={
            "refreshToken": refresh_token,
        })
        assert resp.status_code == 200
        assert "accessToken" in resp.json()["data"]
        assert "refreshToken" in resp.json()["data"]

    @pytest.mark.asyncio
    async def test_list_events_pagination(self, e2e_client):
        client = e2e_client

        resp = await client.post("/api/v1/auth/login", json={
            "email": "admin@college.edu",
            "password": "AdminPass123",
        })
        admin_token = resp.json()["data"]["accessToken"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        resp = await client.get(
            "/api/v1/events?page=1&limit=10", headers=admin_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert body["total"] >= 0
        assert body["page"] == 1
        assert body["limit"] == 10
