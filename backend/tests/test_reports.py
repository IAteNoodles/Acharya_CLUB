import uuid
from unittest.mock import AsyncMock, MagicMock, patch
import pytest


class TestReportService:

    @pytest.mark.asyncio
    async def test_get_dashboard_stats_returns_all_sections(self):
        from app.services.reports import ReportService

        db = AsyncMock()

        def _mock_result(rows):
            mock = MagicMock()
            mock.all.return_value = rows
            return mock

        db.execute = AsyncMock(side_effect=[
            _mock_result([("student", 80), ("teacher", 15), ("admin", 5)]),
            _mock_result([("pending", 5), ("active", 90), ("rejected", 5)]),
            _mock_result([("draft", 5), ("pending", 3), ("approved", 20), ("rejected", 2)]),
            _mock_result([("in_college", 10), ("out_college", 20)]),
            _mock_result([("pending", 30), ("accepted", 150), ("rejected", 20)]),
            _mock_result([("present", 400), ("absent", 80), ("late", 20)]),
        ])

        db.scalar = AsyncMock(side_effect=[1000, 150])

        result = await ReportService.get_dashboard_stats(db)

        assert result.users.total == 100
        assert result.users.by_role == {"student": 80, "teacher": 15, "admin": 5}
        assert result.users.by_status == {"pending": 5, "active": 90, "rejected": 5}

        assert result.events.total == 30
        assert result.events.by_status == {"draft": 5, "pending": 3, "approved": 20, "rejected": 2}
        assert result.events.by_type == {"in_college": 10, "out_college": 20}

        assert result.registrations.total == 200
        assert result.registrations.by_status == {"pending": 30, "accepted": 150, "rejected": 20}

        assert result.attendance.total == 500
        assert result.attendance.by_status == {"present": 400, "absent": 80, "late": 20}

        assert result.notifications.total == 1000
        assert result.notifications.unread == 150

    @pytest.mark.asyncio
    async def test_get_dashboard_stats_empty_db(self):
        from app.services.reports import ReportService

        db = AsyncMock()

        def _mock_result(rows):
            mock = MagicMock()
            mock.all.return_value = rows
            return mock

        db.execute = AsyncMock(side_effect=[
            _mock_result([]),
            _mock_result([]),
            _mock_result([]),
            _mock_result([]),
            _mock_result([]),
            _mock_result([]),
        ])
        db.scalar = AsyncMock(side_effect=[0, 0])

        result = await ReportService.get_dashboard_stats(db)

        assert result.users.total == 0
        assert result.users.by_role == {}
        assert result.events.total == 0
        assert result.registrations.total == 0
        assert result.attendance.total == 0
        assert result.notifications.total == 0
        assert result.notifications.unread == 0


class TestReportsAPI:

    @pytest.mark.asyncio
    async def test_dashboard_returns_stats(self):
        from fastapi import FastAPI
        from app.api.v1.reports import router
        from app.api.deps import get_current_user
        from app.core.exceptions import register_exception_handlers

        app = FastAPI()
        app.include_router(router, prefix="/api/v1/reports")
        register_exception_handlers(app)
        app.dependency_overrides[get_current_user] = lambda: {"sub": str(uuid.uuid4()), "role": "admin"}

        from app.services.reports import ReportService
        from app.schemas.reports import DashboardResponse

        mock_result = DashboardResponse(
            users={"total": 100, "by_role": {"student": 80, "teacher": 15, "admin": 5}, "by_status": {"pending": 5, "active": 90, "rejected": 5}},
            events={"total": 30, "by_status": {"draft": 5, "pending": 3, "approved": 20, "rejected": 2}, "by_type": {"in_college": 10, "out_college": 20}},
            registrations={"total": 200, "by_status": {"pending": 30, "accepted": 150, "rejected": 20}},
            attendance={"total": 500, "by_status": {"present": 400, "absent": 80, "late": 20}},
            notifications={"total": 1000, "unread": 150},
        )

        with patch.object(ReportService, "get_dashboard_stats", new=AsyncMock(return_value=mock_result)):
            from httpx import ASGITransport, AsyncClient
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/reports/dashboard")

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["users"]["total"] == 100
        assert data["data"]["notifications"]["unread"] == 150

    @pytest.mark.asyncio
    async def test_dashboard_forbidden_for_student(self):
        from fastapi import FastAPI
        from app.api.v1.reports import router
        from app.api.deps import get_current_user
        from app.core.exceptions import register_exception_handlers

        app = FastAPI()
        app.include_router(router, prefix="/api/v1/reports")
        register_exception_handlers(app)
        app.dependency_overrides[get_current_user] = lambda: {"sub": str(uuid.uuid4()), "role": "student"}

        from httpx import ASGITransport, AsyncClient
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/reports/dashboard")

        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_dashboard_unauthorized(self):
        from fastapi import FastAPI
        from app.api.v1.reports import router
        from app.api.deps import get_current_user

        app = FastAPI()
        app.include_router(router, prefix="/api/v1/reports")
        app.dependency_overrides[get_current_user] = lambda: None

        from httpx import ASGITransport, AsyncClient
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/reports/dashboard")

        assert resp.status_code == 401
