# Attendance Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement attendance tracking — batch marking (coordinator/admin), attendance sheet view, student self-view, and admin student lookup.

**Architecture:** Add 4 new files (schemas, service, router, tests) and modify `main.py` to register the router. Follows the exact patterns from the Registration module: service class with `@staticmethod` async methods, Pydantic v2 schemas, FastAPI router with dependency injection, mocked tests via `AsyncMock`/`MagicMock`/`httpx.ASGITransport`.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0 async, Pydantic v2, pytest-asyncio

---

### Task 1: Attendance Schemas

**Files:**
- Create: `backend/app/schemas/attendance.py`
- Test: `backend/tests/test_attendance.py` (first section)

- [ ] **Step 1: Write failing schema tests**

```python
import uuid
from datetime import date
import pytest
from pydantic import ValidationError

STUDENT_ID = uuid.uuid4()
EVENT_ID = uuid.uuid4()
TEACHER_ID = uuid.uuid4()


class TestAttendanceSchemas:
    def test_attendance_record_valid_present(self):
        from app.schemas.attendance import AttendanceRecord
        rec = AttendanceRecord(studentId=STUDENT_ID, present=True)
        assert rec.studentId == STUDENT_ID
        assert rec.present is True

    def test_attendance_record_valid_absent(self):
        from app.schemas.attendance import AttendanceRecord
        rec = AttendanceRecord(studentId=STUDENT_ID, present=False)
        assert rec.present is False

    def test_bulk_request_valid(self):
        from app.schemas.attendance import BulkAttendanceRequest, AttendanceRecord
        req = BulkAttendanceRequest(
            eventId=EVENT_ID,
            date=date(2026, 7, 4),
            records=[
                AttendanceRecord(studentId=STUDENT_ID, present=True),
            ],
        )
        assert req.eventId == EVENT_ID

    def test_bulk_request_duplicate_students_rejected(self):
        from app.schemas.attendance import BulkAttendanceRequest, AttendanceRecord
        with pytest.raises(ValidationError):
            BulkAttendanceRequest(
                eventId=EVENT_ID,
                date=date(2026, 7, 4),
                records=[
                    AttendanceRecord(studentId=STUDENT_ID, present=True),
                    AttendanceRecord(studentId=STUDENT_ID, present=False),
                ],
            )

    def test_bulk_request_empty_records_rejected(self):
        from app.schemas.attendance import BulkAttendanceRequest
        with pytest.raises(ValidationError):
            BulkAttendanceRequest(
                eventId=EVENT_ID,
                date=date(2026, 7, 4),
                records=[],
            )

    def test_bulk_request_too_many_records_rejected(self):
        from app.schemas.attendance import BulkAttendanceRequest, AttendanceRecord
        with pytest.raises(ValidationError):
            BulkAttendanceRequest(
                eventId=EVENT_ID,
                date=date(2026, 7, 4),
                records=[AttendanceRecord(studentId=uuid.uuid4(), present=True) for _ in range(101)],
            )

    def test_bulk_response(self):
        from app.schemas.attendance import BulkAttendanceResponse
        resp = BulkAttendanceResponse(count=45, message="Attendance marked for 45 students")
        assert resp.count == 45
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend
python -m pytest tests/test_attendance.py::TestAttendanceSchemas -v 2>&1
```

Expected: ModuleNotFoundError / ImportError

- [ ] **Step 3: Write schema file**

```python
import uuid
from datetime import date
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class AttendanceRecord(BaseModel):
    studentId: uuid.UUID
    present: bool


class BulkAttendanceRequest(BaseModel):
    eventId: uuid.UUID
    date: date
    records: list[AttendanceRecord]

    @field_validator("records")
    @classmethod
    def validate_records_count(cls, v: list) -> list:
        if len(v) < 1:
            raise ValueError("At least one record is required")
        if len(v) > 100:
            raise ValueError("Maximum 100 records per batch")
        return v

    @model_validator(mode="after")
    def check_duplicate_students(self) -> "BulkAttendanceRequest":
        student_ids = [str(r.studentId) for r in self.records]
        if len(student_ids) != len(set(student_ids)):
            raise ValueError("Duplicate student IDs in batch")
        return self


class BulkAttendanceResponse(BaseModel):
    success: bool = True
    count: int
    message: str


class StudentBrief(BaseModel):
    id: str
    name: str
    email: str

    model_config = {"from_attributes": True}


class MarkerBrief(BaseModel):
    id: str
    name: str

    model_config = {"from_attributes": True}


class AttendanceRecordResponse(BaseModel):
    success: bool = True
    id: str
    event_id: str
    student_id: str
    date: date
    status: str
    marked_by: str
    marked_at: str

    model_config = {"from_attributes": True}


class AttendanceWithStudentResponse(BaseModel):
    success: bool = True
    id: str
    event_id: str
    student_id: str
    date: date
    status: str
    student: Optional[StudentBrief] = None
    marked_by: Optional[MarkerBrief] = None

    model_config = {"from_attributes": True}


class AttendanceWithEventResponse(BaseModel):
    success: bool = True
    id: str
    event_id: str
    student_id: str
    date: date
    status: str
    event: Optional[dict] = None

    model_config = {"from_attributes": True}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd backend
python -m pytest tests/test_attendance.py::TestAttendanceSchemas -v 2>&1
```

Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/attendance.py backend/tests/test_attendance.py
git commit -m "feat(attendance): add Pydantic schemas for attendance module"
```

---

### Task 2: Attendance Service

**Files:**
- Create: `backend/app/services/attendance.py`
- Test: `backend/tests/test_attendance.py` (add service tests)

- [ ] **Step 1: Write failing service tests**

Add these after `TestAttendanceSchemas` in `test_attendance.py`:

```python
class TestAttendanceService:
    @pytest.mark.asyncio
    async def test_mark_bulk_success(self):
        from app.services.attendance import AttendanceService
        from datetime import date

        db = AsyncMock()
        mock_event = MagicMock()
        mock_event.coordinator_id = uuid.UUID(str(TEACHER_ID))
        db.get.return_value = mock_event
        db.execute.return_value = MagicMock(
            scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[MagicMock()])))
        )

        records_data = [{"studentId": STUDENT_ID, "present": True}]
        result = await AttendanceService.mark_bulk(
            db, EVENT_ID, date(2026, 7, 4), records_data,
            {"sub": str(TEACHER_ID), "role": "teacher"},
        )

        assert result["count"] == 1
        db.add.assert_called_once()
        db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_mark_bulk_event_not_found(self):
        from app.services.attendance import AttendanceService
        from datetime import date

        db = AsyncMock()
        db.get.return_value = None

        with pytest.raises(NotFoundException):
            await AttendanceService.mark_bulk(
                db, EVENT_ID, date(2026, 7, 4), [],
                {"sub": str(TEACHER_ID), "role": "teacher"},
            )

    @pytest.mark.asyncio
    async def test_mark_bulk_forbidden_not_coordinator(self):
        from app.services.attendance import AttendanceService
        from datetime import date

        db = AsyncMock()
        mock_event = MagicMock()
        mock_event.coordinator_id = uuid.uuid4()
        db.get.return_value = mock_event

        with pytest.raises(ForbiddenException):
            await AttendanceService.mark_bulk(
                db, EVENT_ID, date(2026, 7, 4), [],
                {"sub": str(TEACHER_ID), "role": "teacher"},
            )

    @pytest.mark.asyncio
    async def test_mark_bulk_admin_bypass(self):
        from app.services.attendance import AttendanceService
        from datetime import date

        db = AsyncMock()
        mock_event = MagicMock()
        mock_event.coordinator_id = uuid.uuid4()
        db.get.return_value = mock_event
        db.execute.return_value = MagicMock(
            scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[MagicMock()])))
        )

        result = await AttendanceService.mark_bulk(
            db, EVENT_ID, date(2026, 7, 4),
            [{"studentId": STUDENT_ID, "present": True}],
            {"sub": str(uuid.uuid4()), "role": "admin"},
        )

        assert result["count"] == 1

    @pytest.mark.asyncio
    async def test_mark_bulk_student_not_registered(self):
        from app.services.attendance import AttendanceService
        from datetime import date

        db = AsyncMock()
        mock_event = MagicMock()
        mock_event.coordinator_id = uuid.UUID(str(TEACHER_ID))
        db.get.return_value = mock_event
        db.execute.return_value = MagicMock(
            scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        )

        with pytest.raises(ConflictException, match="not registered"):
            await AttendanceService.mark_bulk(
                db, EVENT_ID, date(2026, 7, 4),
                [{"studentId": STUDENT_ID, "present": True}],
                {"sub": str(TEACHER_ID), "role": "teacher"},
            )

    @pytest.mark.asyncio
    async def test_mark_bulk_upsert_existing_record(self):
        from app.services.attendance import AttendanceService
        from datetime import date

        db = AsyncMock()
        mock_event = MagicMock()
        mock_event.coordinator_id = uuid.UUID(str(TEACHER_ID))
        mock_event.status = "approved"
        db.get.return_value = mock_event

        mock_reg = MagicMock()
        mock_reg.student_id = STUDENT_ID
        db.execute.return_value = MagicMock(
            scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[mock_reg])))
        )

        mock_existing = MagicMock()
        mock_existing.status = "absent"

        result = await AttendanceService.mark_bulk(
            db, EVENT_ID, date(2026, 7, 4),
            [{"studentId": STUDENT_ID, "present": True}],
            {"sub": str(TEACHER_ID), "role": "teacher"},
        )

        assert result["count"] == 1

    @pytest.mark.asyncio
    async def test_get_event_attendance_success(self):
        from app.services.attendance import AttendanceService

        db = AsyncMock()
        mock_event = MagicMock()
        mock_event.coordinator_id = uuid.UUID(str(TEACHER_ID))
        db.get.return_value = mock_event
        count_result = MagicMock()
        count_result.scalar_one.return_value = 1
        att = MagicMock()
        att.id = uuid.uuid4()
        att.event_id = EVENT_ID
        att.student_id = STUDENT_ID
        att.date = "2026-07-04"
        att.status = "present"
        att.marked_by = MagicMock()
        att.marked_by.id = TEACHER_ID
        att.marked_by.name = "Dr. Rajesh"
        att.student = MagicMock()
        att.student.id = STUDENT_ID
        att.student.name = "Priya Singh"
        att.student.email = "priya@college.edu"
        data_result = MagicMock()
        data_result.scalars.return_value = MagicMock(all=MagicMock(return_value=[att]))
        db.execute = AsyncMock(side_effect=[count_result, data_result])

        records, total = await AttendanceService.get_event_attendance(
            db, EVENT_ID, {"sub": str(TEACHER_ID), "role": "teacher"},
            page=1, limit=20,
        )

        assert total == 1
        records_list = list(records)
        assert len(records_list) == 1

    @pytest.mark.asyncio
    async def test_get_event_attendance_forbidden(self):
        from app.services.attendance import AttendanceService

        db = AsyncMock()
        mock_event = MagicMock()
        mock_event.coordinator_id = uuid.uuid4()
        db.get.return_value = mock_event

        with pytest.raises(ForbiddenException):
            await AttendanceService.get_event_attendance(
                db, EVENT_ID, {"sub": str(STUDENT_ID), "role": "student"},
            )

    @pytest.mark.asyncio
    async def test_get_student_attendance_success(self):
        from app.services.attendance import AttendanceService

        db = AsyncMock()
        count_result = MagicMock()
        count_result.scalar_one.return_value = 1
        att = MagicMock()
        att.id = uuid.uuid4()
        att.event_id = EVENT_ID
        att.student_id = STUDENT_ID
        att.date = "2026-07-04"
        att.status = "present"
        att.event = MagicMock()
        att.event.id = EVENT_ID
        att.event.title = "Tech Fest"
        att.event.event_type = "in_college"
        att.event.start_date = "2026-07-04T00:00:00Z"
        att.event.end_date = "2026-07-05T00:00:00Z"
        data_result = MagicMock()
        data_result.scalars.return_value = MagicMock(all=MagicMock(return_value=[att]))
        db.execute = AsyncMock(side_effect=[count_result, data_result])

        records, total = await AttendanceService.get_student_attendance(
            db, str(STUDENT_ID), page=1, limit=20,
        )

        assert total == 1
```

- [ ] **Step 2: Run schema tests + new service tests**

```bash
cd backend
python -m pytest tests/test_attendance.py -v 2>&1
```

Expected: New service tests fail (ImportError or AttributeError)

- [ ] **Step 3: Write attendance service**

```python
import uuid
from datetime import date
from typing import Optional

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.exceptions import NotFoundException, ForbiddenException, ConflictException
from app.models.event import Event
from app.models.attendance import Attendance, AttendanceStatus
from app.models.registration import Registration, RegistrationStatus


class AttendanceService:

    @staticmethod
    async def mark_bulk(
        db: AsyncSession,
        event_id: uuid.UUID,
        att_date: date,
        records: list[dict],
        current_user: dict,
    ) -> dict:
        event = await db.get(Event, event_id)
        if not event:
            raise NotFoundException("Event not found")

        user_id = uuid.UUID(current_user["sub"])
        if current_user["role"] != "admin" and event.coordinator_id != user_id:
            raise ForbiddenException("You are not the coordinator of this event")

        student_ids = [r["studentId"] for r in records]
        reg_result = await db.execute(
            select(Registration).where(
                Registration.event_id == event_id,
                Registration.student_id.in_(student_ids),
                Registration.status == RegistrationStatus.ACCEPTED,
            )
        )
        registered_student_ids = {str(r.student_id) for r in reg_result.scalars().all()}

        for r in records:
            if str(r["studentId"]) not in registered_student_ids:
                raise ConflictException(f"Student {r['studentId']} is not registered for this event")

        count = 0
        for r in records:
            status = AttendanceStatus.PRESENT if r["present"] else AttendanceStatus.ABSENT

            existing = await db.execute(
                select(Attendance).where(
                    Attendance.event_id == event_id,
                    Attendance.student_id == r["studentId"],
                    Attendance.date == att_date,
                )
            )
            att = existing.scalar_one_or_none()
            if att:
                att.status = status
                att.marked_by_id = user_id
            else:
                att = Attendance(
                    event_id=event_id,
                    student_id=r["studentId"],
                    marked_by_id=user_id,
                    date=att_date,
                    status=status,
                )
                db.add(att)
            count += 1

        await db.commit()
        return {"count": count, "message": f"Attendance marked for {count} students"}

    @staticmethod
    async def get_event_attendance(
        db: AsyncSession,
        event_id: uuid.UUID,
        current_user: dict,
        att_date: Optional[date] = None,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[Attendance], int]:
        event = await db.get(Event, event_id)
        if not event:
            raise NotFoundException("Event not found")

        user_id = uuid.UUID(current_user["sub"])
        if current_user["role"] != "admin" and event.coordinator_id != user_id:
            raise ForbiddenException("You are not the coordinator of this event")

        stmt = (
            select(Attendance)
            .options(joinedload(Attendance.student), joinedload(Attendance.marker))
            .where(Attendance.event_id == event_id)
        )
        count_stmt = select(func.count()).select_from(Attendance).where(Attendance.event_id == event_id)

        if att_date:
            stmt = stmt.where(Attendance.date == att_date)
            count_stmt = count_stmt.where(Attendance.date == att_date)

        count_result = await db.execute(count_stmt)
        total = count_result.scalar_one()

        stmt = (
            stmt
            .order_by(Attendance.date.desc(), Attendance.student_id)
            .offset((page - 1) * limit)
            .limit(limit)
        )

        result = await db.execute(stmt)
        records = list(result.scalars().all())

        return records, total

    @staticmethod
    async def get_student_attendance(
        db: AsyncSession,
        student_id: str,
        event_id: Optional[uuid.UUID] = None,
        status_filter: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[Attendance], int]:
        stmt = (
            select(Attendance)
            .options(joinedload(Attendance.event))
            .where(Attendance.student_id == student_id)
        )
        count_stmt = select(func.count()).select_from(Attendance).where(Attendance.student_id == student_id)

        if event_id:
            stmt = stmt.where(Attendance.event_id == event_id)
            count_stmt = count_stmt.where(Attendance.event_id == event_id)

        if status_filter:
            stmt = stmt.where(Attendance.status == status_filter)
            count_stmt = count_stmt.where(Attendance.status == status_filter)

        count_result = await db.execute(count_stmt)
        total = count_result.scalar_one()

        stmt = (
            stmt
            .order_by(Attendance.date.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )

        result = await db.execute(stmt)
        records = list(result.scalars().all())

        return records, total
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend
python -m pytest tests/test_attendance.py -v 2>&1
```

Expected: All tests pass

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/attendance.py backend/tests/test_attendance.py
git commit -m "feat(attendance): add AttendanceService with bulk mark and query methods"
```

---

### Task 3: Attendance Router

**Files:**
- Create: `backend/app/api/v1/attendance.py`
- Modify: `backend/app/main.py` (add router import + app.include_router)

- [ ] **Step 1: Write failing API tests**

Add after `TestAttendanceService` in `test_attendance.py`:

```python
@pytest.fixture
def coordinator_app():
    from fastapi import FastAPI
    from app.api.v1.attendance import router
    from app.core.exceptions import register_exception_handlers
    from app.api import deps

    app = FastAPI()
    app.include_router(router)
    register_exception_handlers(app)

    async def mock_user():
        return {"sub": str(TEACHER_ID), "role": "teacher"}

    app.dependency_overrides[deps.get_current_user] = mock_user
    return app


@pytest.fixture
def admin_app():
    from fastapi import FastAPI
    from app.api.v1.attendance import router
    from app.core.exceptions import register_exception_handlers
    from app.api import deps

    app = FastAPI()
    app.include_router(router)
    register_exception_handlers(app)

    async def mock_user():
        return {"sub": str(uuid.uuid4()), "role": "admin"}

    app.dependency_overrides[deps.get_current_user] = mock_user
    return app


@pytest.fixture
def student_att_app():
    from fastapi import FastAPI
    from app.api.v1.attendance import router
    from app.core.exceptions import register_exception_handlers
    from app.api import deps

    app = FastAPI()
    app.include_router(router)
    register_exception_handlers(app)

    async def mock_user():
        return {"sub": str(STUDENT_ID), "role": "student"}

    app.dependency_overrides[deps.get_current_user] = mock_user
    return app


class TestAttendanceAPI:
    @pytest.mark.asyncio
    async def test_bulk_attendance_200(self, coordinator_app):
        from datetime import date
        with patch("app.services.attendance.AttendanceService.mark_bulk", return_value={"count": 1, "message": "ok"}):
            transport = ASGITransport(app=coordinator_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/attendance/bulk",
                    json={
                        "eventId": str(EVENT_ID),
                        "date": "2026-07-04",
                        "records": [{"studentId": str(STUDENT_ID), "present": True}],
                    },
                )

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["count"] == 1

    @pytest.mark.asyncio
    async def test_bulk_attendance_validation_error(self, coordinator_app):
        transport = ASGITransport(app=coordinator_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/attendance/bulk",
                json={"eventId": str(EVENT_ID), "date": "2026-07-04", "records": []},
            )

        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_bulk_attendance_forbidden(self, student_att_app):
        from datetime import date
        transport = ASGITransport(app=student_att_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/attendance/bulk",
                json={
                    "eventId": str(EVENT_ID),
                    "date": "2026-07-04",
                    "records": [{"studentId": str(STUDENT_ID), "present": True}],
                },
            )

        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_bulk_attendance_not_found(self, coordinator_app):
        with patch("app.services.attendance.AttendanceService.mark_bulk") as mock_mark:
            mock_mark.side_effect = NotFoundException("Event not found")
            transport = ASGITransport(app=coordinator_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/attendance/bulk",
                    json={
                        "eventId": str(EVENT_ID),
                        "date": "2026-07-04",
                        "records": [{"studentId": str(STUDENT_ID), "present": True}],
                    },
                )

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_event_attendance_200(self, coordinator_app):
        mock_att = MagicMock()
        mock_att.id = uuid.uuid4()
        mock_att.event_id = EVENT_ID
        mock_att.student_id = STUDENT_ID
        mock_att.date = "2026-07-04"
        mock_att.status = "present"
        mock_att.student = MagicMock()
        mock_att.student.id = STUDENT_ID
        mock_att.student.name = "Priya"
        mock_att.student.email = "priya@college.edu"
        mock_att.marked_by = MagicMock()
        mock_att.marked_by.id = TEACHER_ID
        mock_att.marked_by.name = "Dr. Rajesh"

        with patch("app.services.attendance.AttendanceService.get_event_attendance", return_value=([mock_att], 1)):
            transport = ASGITransport(app=coordinator_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(f"/api/v1/attendance/event/{EVENT_ID}")

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert len(data["data"]) == 1

    @pytest.mark.asyncio
    async def test_get_my_attendance_200(self, student_att_app):
        mock_att = MagicMock()
        mock_att.id = uuid.uuid4()
        mock_att.event_id = EVENT_ID
        mock_att.student_id = STUDENT_ID
        mock_att.date = "2026-07-04"
        mock_att.status = "present"
        mock_att.event = MagicMock()
        mock_att.event.id = EVENT_ID
        mock_att.event.title = "Tech Fest"
        mock_att.event.event_type = "in_college"
        mock_att.event.start_date = "2026-07-04T00:00:00Z"
        mock_att.event.end_date = "2026-07-05T00:00:00Z"

        with patch("app.services.attendance.AttendanceService.get_student_attendance", return_value=([mock_att], 1)):
            transport = ASGITransport(app=student_att_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/attendance/my")

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_get_student_attendance_as_admin(self, admin_app):
        mock_att = MagicMock()
        mock_att.id = uuid.uuid4()
        mock_att.event_id = EVENT_ID
        mock_att.student_id = STUDENT_ID
        mock_att.date = "2026-07-04"
        mock_att.status = "present"
        mock_att.event = MagicMock()
        mock_att.event.id = EVENT_ID
        mock_att.event.title = "Tech Fest"
        mock_att.event.event_type = "in_college"
        mock_att.event.start_date = "2026-07-04T00:00:00Z"
        mock_att.event.end_date = "2026-07-05T00:00:00Z"

        with patch("app.services.attendance.AttendanceService.get_student_attendance", return_value=([mock_att], 1)):
            transport = ASGITransport(app=admin_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(f"/api/v1/attendance/student/{STUDENT_ID}")

        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_student_cannot_access_event_attendance(self, student_att_app):
        transport = ASGITransport(app=student_att_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"/api/v1/attendance/event/{EVENT_ID}")

        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_unauthorized_access_to_attendance(self):
        from fastapi import FastAPI
        from app.api.v1.attendance import router

        app = FastAPI()
        app.include_router(router)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/attendance/my")
            assert resp.status_code == 401
```

- [ ] **Step 2: Run these tests to verify they fail**

```bash
cd backend
python -m pytest tests/test_attendance.py -v 2>&1
```

Expected: API tests fail (ImportError — router not found)

- [ ] **Step 3: Create the router file**

```python
import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin
from app.core.database import get_db
from app.schemas.common import SuccessResponse, PaginatedResponse, PaginatedMeta
from app.schemas.attendance import (
    AttendanceWithStudentResponse,
    AttendanceWithEventResponse,
    BulkAttendanceRequest,
    BulkAttendanceResponse,
    StudentBrief,
    MarkerBrief,
)
from app.services.attendance import AttendanceService

router = APIRouter(prefix="/api/v1/attendance", tags=["Attendance"])


@router.post("/bulk")
async def mark_bulk_attendance(
    request: BulkAttendanceRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    records_dict = [{"studentId": r.studentId, "present": r.present} for r in request.records]
    result = await AttendanceService.mark_bulk(
        db, request.eventId, request.date, records_dict, current_user,
    )
    return SuccessResponse(data=BulkAttendanceResponse(**result))


@router.get("/event/{event_id}")
async def get_event_attendance(
    event_id: uuid.UUID,
    att_date: Optional[date] = Query(None, alias="date"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    records, total = await AttendanceService.get_event_attendance(
        db, event_id, current_user, att_date=att_date, page=page, limit=limit,
    )
    total_pages = max(1, (total + limit - 1) // limit) if total else 0
    return PaginatedResponse(
        success=True,
        data=[_att_to_student_response(r) for r in records],
        meta=PaginatedMeta(page=page, limit=limit, total=total, total_pages=total_pages),
    )


@router.get("/my")
async def get_my_attendance(
    event_id: Optional[uuid.UUID] = Query(None, alias="eventId"),
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    records, total = await AttendanceService.get_student_attendance(
        db, current_user["sub"], event_id=event_id, status_filter=status_filter,
        page=page, limit=limit,
    )
    total_pages = max(1, (total + limit - 1) // limit) if total else 0
    return PaginatedResponse(
        success=True,
        data=[_att_to_event_response(r) for r in records],
        meta=PaginatedMeta(page=page, limit=limit, total=total, total_pages=total_pages),
    )


@router.get("/student/{student_id}")
async def get_student_attendance(
    student_id: uuid.UUID,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    records, total = await AttendanceService.get_student_attendance(
        db, str(student_id), page=page, limit=limit,
    )
    total_pages = max(1, (total + limit - 1) // limit) if total else 0
    return PaginatedResponse(
        success=True,
        data=[_att_to_event_response(r) for r in records],
        meta=PaginatedMeta(page=page, limit=limit, total=total, total_pages=total_pages),
    )


def _att_to_student_response(att) -> AttendanceWithStudentResponse:
    student = att.student if hasattr(att, "student") and att.student else None
    marker = att.marker if hasattr(att, "marker") and att.marker else None
    return AttendanceWithStudentResponse(
        id=str(att.id),
        event_id=str(att.event_id),
        student_id=str(att.student_id),
        date=att.date,
        status=att.status.value if hasattr(att.status, "value") else att.status,
        student=StudentBrief(id=str(student.id), name=student.name, email=student.email) if student else None,
        marked_by=MarkerBrief(id=str(marker.id), name=marker.name) if marker else None,
    )


def _att_to_event_response(att) -> AttendanceWithEventResponse:
    event = att.event if hasattr(att, "event") and att.event else None
    return AttendanceWithEventResponse(
        id=str(att.id),
        event_id=str(att.event_id),
        student_id=str(att.student_id),
        date=att.date,
        status=att.status.value if hasattr(att.status, "value") else att.status,
        event={
            "id": str(event.id),
            "title": event.title,
            "event_type": event.event_type.value if hasattr(event.event_type, "value") else event.event_type,
            "start_date": str(event.start_date),
            "end_date": str(event.end_date),
        } if event else None,
    )
```

- [ ] **Step 4: Register the router in main.py**

In `backend/app/main.py`, add the import line after line 12:
```python
from app.api.v1.attendance import router as attendance_router
```

Add the include line after line 116:
```python
    app.include_router(attendance_router)
```

Also add the tag:
```python
{"name": "Attendance", "description": "Attendance tracking"},
```

- [ ] **Step 5: Run all tests to verify they pass**

```bash
cd backend
python -m pytest tests/test_attendance.py -v 2>&1
```

Expected: All attendance tests pass

```bash
cd backend
python -m pytest --tb=short 2>&1
```

Expected: All 165 + ~21 = ~186 tests pass

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/v1/attendance.py backend/app/main.py backend/tests/test_attendance.py
git commit -m "feat(attendance): add attendance router with bulk mark, event sheet, my records, admin lookup"
```

---

### Task 4: Update API Spec

**Files:**
- Modify: `backend/docs/api-specification.md`

- [ ] **Step 1: Update section 11 in api-specification.md** to reflect the actual 4-endpoint implementation (bulk only, no single `/mark`, add `/student/{studentId}`)

- [ ] **Step 2: Commit**

```bash
git add docs/api-specification.md
git commit -m "docs(attendance): update API spec to match actual attendance endpoints"
```
