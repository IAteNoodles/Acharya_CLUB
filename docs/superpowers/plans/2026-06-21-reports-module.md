# Reports/Dashboard — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Single dashboard endpoint returning aggregated counts across all entities.

**Architecture:** `ReportService.get_dashboard_stats()` runs 8 independent async COUNT queries concurrently via `asyncio.gather()`. Single `GET /api/v1/reports/dashboard` endpoint behind `require_teacher_or_admin`.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 async, asyncio.gather

---

## File Map

| Action | File | Responsibility |
|---|---|---|
| CREATE | `app/schemas/reports.py` | Dashboard response Pydantic schemas |
| CREATE | `app/services/reports.py` | ReportService with get_dashboard_stats |
| CREATE | `app/api/v1/reports.py` | GET /api/v1/reports/dashboard endpoint |
| MODIFY | `app/main.py` | Register reports router + tag |
| CREATE | `tests/test_reports.py` | All tests (schema, service, API) |

---

### Task 1: Reports Schemas

**Files:**
- Create: `app/schemas/reports.py`

- [ ] **Step 1: Create `app/schemas/reports.py`**

```python
from pydantic import BaseModel


class UserStats(BaseModel):
    total: int
    by_role: dict
    by_status: dict


class EventStats(BaseModel):
    total: int
    by_status: dict
    by_type: dict


class RegistrationStats(BaseModel):
    total: int
    by_status: dict


class AttendanceStats(BaseModel):
    total: int
    by_status: dict


class NotificationStats(BaseModel):
    total: int
    unread: int


class DashboardResponse(BaseModel):
    users: UserStats
    events: EventStats
    registrations: RegistrationStats
    attendance: AttendanceStats
    notifications: NotificationStats
```

- [ ] **Step 2: Verify schemas import correctly**

Run: `python -c "from app.schemas.reports import DashboardResponse, UserStats, EventStats, RegistrationStats, AttendanceStats, NotificationStats; print('OK')"`
Expected: OK

- [ ] **Step 3: Commit**

```bash
git add app/schemas/reports.py
git commit -m "feat(reports): add dashboard response schemas"
```

---

### Task 2: Reports Service + Tests

**Files:**
- Create: `app/services/reports.py`
- Create: `tests/test_reports.py`

- [ ] **Step 1: Write service tests in `tests/test_reports.py`**

```python
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
import pytest


class TestReportService:

    @pytest.mark.asyncio
    async def test_get_dashboard_stats_returns_all_sections(self):
        from app.services.reports import ReportService

        db = AsyncMock()

        # Mock scalars for each GROUP BY query to return list of Row-like objects
        def _mock_result(rows):
            """rows is a list of (group_key, count) tuples"""
            mock = MagicMock()
            mock.all.return_value = rows
            return mock

        # db.execute returns a result with .all() 
        db.execute = AsyncMock(side_effect=[
            _mock_result([("student", 80), ("teacher", 15), ("admin", 5)]),       # users by role
            _mock_result([("pending", 5), ("active", 90), ("rejected", 5)]),       # users by status
            _mock_result([("draft", 5), ("pending", 3), ("approved", 20), ("rejected", 2)]),  # events by status
            _mock_result([("in_college", 10), ("out_college", 20)]),               # events by type
            _mock_result([("pending", 30), ("accepted", 150), ("rejected", 20)]),  # registrations by status
            _mock_result([("present", 400), ("absent", 80), ("late", 20)]),        # attendance by status
        ])

        # db.scalar for notification counts
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
            _mock_result([]),  # no users
            _mock_result([]),  # no users by status
            _mock_result([]),  # no events
            _mock_result([]),  # no event types
            _mock_result([]),  # no registrations
            _mock_result([]),  # no attendance
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
```

- [ ] **Step 2: Run tests (expect failure)**

Run: `pytest tests/test_reports.py::TestReportService -v`
Expected: ModuleNotFoundError for app.services.reports

- [ ] **Step 3: Create `app/services/reports.py`**

```python
import asyncio
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.event import Event
from app.models.registration import Registration
from app.models.attendance import Attendance
from app.models.notification import Notification
from app.schemas.reports import (
    DashboardResponse, UserStats, EventStats,
    RegistrationStats, AttendanceStats, NotificationStats,
)


def _grouped_counts(rows) -> dict:
    """Convert a list of (key, count) rows from GROUP BY into a dict."""
    return {str(r[0]): r[1] for r in rows}


def _total_from_counts(counts: dict) -> int:
    return sum(counts.values())


class ReportService:

    @staticmethod
    async def get_dashboard_stats(db: AsyncSession) -> DashboardResponse:
        async def count_users_by_role():
            r = await db.execute(
                select(User.role, func.count()).group_by(User.role)
            )
            return _grouped_counts(r.all())

        async def count_users_by_status():
            r = await db.execute(
                select(User.status, func.count()).group_by(User.status)
            )
            return _grouped_counts(r.all())

        async def count_events_by_status():
            r = await db.execute(
                select(Event.status, func.count()).group_by(Event.status)
            )
            return _grouped_counts(r.all())

        async def count_events_by_type():
            r = await db.execute(
                select(Event.event_type, func.count()).group_by(Event.event_type)
            )
            return _grouped_counts(r.all())

        async def count_registrations_by_status():
            r = await db.execute(
                select(Registration.status, func.count()).group_by(Registration.status)
            )
            return _grouped_counts(r.all())

        async def count_attendance_by_status():
            r = await db.execute(
                select(Attendance.status, func.count()).group_by(Attendance.status)
            )
            return _grouped_counts(r.all())

        async def count_notifications_total():
            return await db.scalar(select(func.count(Notification.id))) or 0

        async def count_notifications_unread():
            return await db.scalar(
                select(func.count(Notification.id)).where(Notification.is_read == False)
            ) or 0

        (
            users_by_role,
            users_by_status,
            events_by_status,
            events_by_type,
            regs_by_status,
            att_by_status,
            notif_total,
            notif_unread,
        ) = await asyncio.gather(
            count_users_by_role(),
            count_users_by_status(),
            count_events_by_status(),
            count_events_by_type(),
            count_registrations_by_status(),
            count_attendance_by_status(),
            count_notifications_total(),
            count_notifications_unread(),
        )

        return DashboardResponse(
            users=UserStats(
                total=_total_from_counts(users_by_role),
                by_role=users_by_role,
                by_status=users_by_status,
            ),
            events=EventStats(
                total=_total_from_counts(events_by_status),
                by_status=events_by_status,
                by_type=events_by_type,
            ),
            registrations=RegistrationStats(
                total=_total_from_counts(regs_by_status),
                by_status=regs_by_status,
            ),
            attendance=AttendanceStats(
                total=_total_from_counts(att_by_status),
                by_status=att_by_status,
            ),
            notifications=NotificationStats(
                total=notif_total,
                unread=notif_unread,
            ),
        )
```

- [ ] **Step 4: Run tests (should pass)**

Run: `pytest tests/test_reports.py::TestReportService -v`
Expected: All pass

- [ ] **Step 5: Run full suite to verify no regressions**

Run: `pytest --tb=line`
Expected: All pass (223+ tests)

- [ ] **Step 6: Commit**

```bash
git add app/services/reports.py tests/test_reports.py
git commit -m "feat(reports): add ReportService with dashboard stats + tests"
```

---

### Task 3: Reports Router + API Test + Register in main.py

**Files:**
- Create: `app/api/v1/reports.py`
- Modify: `tests/test_reports.py` (append API test)
- Modify: `app/main.py` (register router + tag)

- [ ] **Step 1: Append API test to `tests/test_reports.py`**

```python
class TestReportsAPI:

    @pytest.mark.asyncio
    async def test_dashboard_returns_stats(self):
        from fastapi import FastAPI
        from app.api.v1.reports import router
        from app.api.deps import get_current_user
        from app.core.exceptions import register_exception_handlers

        app = FastAPI()
        app.include_router(router)
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
        app.include_router(router)
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
        app.include_router(router)
        app.dependency_overrides[get_current_user] = lambda: None

        from httpx import ASGITransport, AsyncClient
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/reports/dashboard")

        assert resp.status_code == 401
```

- [ ] **Step 2: Run API tests (expect failure)**

Run: `pytest tests/test_reports.py::TestReportsAPI -v`
Expected: ModuleNotFoundError for app.api.v1.reports

- [ ] **Step 3: Create `app/api/v1/reports.py`**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user, require_teacher_or_admin
from app.core.database import get_db
from app.schemas.common import SuccessResponse
from app.services.reports import ReportService

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


@router.get("/dashboard")
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_teacher_or_admin),
):
    stats = await ReportService.get_dashboard_stats(db)
    return SuccessResponse(data=stats)
```

- [ ] **Step 4: Run API tests (should pass)**

Run: `pytest tests/test_reports.py::TestReportsAPI -v`
Expected: All pass

- [ ] **Step 5: Register router in `app/main.py`**

Add import:
```python
from app.api.v1.reports import router as reports_router
```

Add `include_router`:
```python
app.include_router(reports_router)
```

Add to `openapi_tags`:
```python
{"name": "reports", "description": "Reports and dashboard"},
```

- [ ] **Step 6: Run full suite**

Run: `pytest --tb=line`
Expected: All tests pass

- [ ] **Step 7: Commit**

```bash
git add app/api/v1/reports.py tests/test_reports.py app/main.py
git commit -m "feat(reports): add dashboard endpoint + API tests + register router"
```
