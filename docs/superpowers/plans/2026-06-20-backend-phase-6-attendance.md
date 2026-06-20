# Phase 6: Attendance Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement attendance tracking system with single mark, bulk mark, and attendance sheet retrieval.

**Architecture:** Attendance module uses upsert patterns and SQLAlchemy async transactions for bulk operations. The teacher can only mark attendance for events where they are the assigned coordinator. The `Attendance` model stores `present: bool` directly. Event attendance sheets are built by left-joining accepted registrations with attendance records for the given date.

**Tech Stack:** Python 3.12+, FastAPI, SQLAlchemy 2.0 async (asyncio extension), Pydantic v2, pytest, httpx (async test client)

**Assumptions:** Phases 1-5 are complete. The `backend/app/` directory exists with:
- Auth: `get_current_user` dependency, role-based `RoleChecker` (e.g., `RoleChecker(['teacher', 'admin'])`)
- Exceptions: `HTTPException` subclasses or custom `AppHTTPException` with `detail` dict
- Config: `backend/app/core/config.py` with settings, `backend/app/db/session.py` with `async_session`
- SQLAlchemy models: `User`, `Event`, `Registration`, `Attendance` (all with `uuid` PKs), `Attendance` has `__table_args__: UniqueConstraint('event_id', 'student_id', 'date')`
- Events module complete with coordinator assignment (`event.coordinator_id`)
- Registration module complete with accepted status workflow
- Router mounting point ready in `backend/app/main.py`

---

## File Structure

```
backend/app/schemas/
├── attendance.py                # Pydantic request/response schemas

backend/app/services/
├── attendance.py                # Business logic (4 async functions)

backend/app/api/v1/
├── attendance.py                # FastAPI router with dependencies

backend/tests/
├── test_attendance.py           # Integration tests (async httpx)

Modified:
backend/app/main.py              # Include attendance router
```

---

## Tasks

### Task 1: Create Pydantic schemas for all attendance endpoints

**Files:**
- Create: `backend/app/schemas/attendance.py`

- [ ] **Step 1: Write schemas implementation**

```python
from datetime import date
from uuid import UUID
from pydantic import BaseModel, Field, model_validator
from typing import Optional


class MarkAttendanceRequest(BaseModel):
    event_id: UUID
    student_id: UUID
    date: date
    present: bool


class BulkAttendanceRecord(BaseModel):
    student_id: UUID
    present: bool


class BulkAttendanceRequest(BaseModel):
    event_id: UUID
    date: date
    records: list[BulkAttendanceRecord]

    @model_validator(mode='after')
    def check_records_not_empty(self):
        if not self.records:
            raise ValueError('At least one attendance record is required')
        return self


class AttendanceResponse(BaseModel):
    id: UUID
    event_id: UUID
    student_id: UUID
    date: date
    present: bool
    marked_by_id: UUID

    model_config = {'from_attributes': True}


class StudentInfo(BaseModel):
    id: UUID
    name: str
    email: str


class AttendanceSheetRow(BaseModel):
    student: StudentInfo
    present: Optional[bool] = None


class AttendanceSheetResponse(BaseModel):
    attendance: list[AttendanceSheetRow]


class BulkAttendanceResponse(BaseModel):
    count: int


class StudentAttendanceRecord(BaseModel):
    id: UUID
    event_id: UUID
    event_title: str
    date: date
    present: bool

    model_config = {'from_attributes': True}


class PaginatedAttendanceResponse(BaseModel):
    data: list[StudentAttendanceRecord]
    page: int
    limit: int
    total: int
    total_pages: int
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/schemas/attendance.py
git commit -m "feat: add Pydantic schemas for attendance module (mark, bulk, event sheet, student records)"
```

---

### Task 2: Create attendance service with all business logic

**Files:**
- Create: `backend/app/services/attendance.py`

- [ ] **Step 1: Write service implementation**

```python
from datetime import date
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event
from app.models.registration import Registration, RegistrationStatus
from app.models.attendance import Attendance
from app.schemas.attendance import (
    MarkAttendanceRequest,
    BulkAttendanceRequest,
    PaginatedAttendanceResponse,
    StudentAttendanceRecord,
)
from app.core.exceptions import NotFoundException, ForbiddenException, ValidationException


class AttendanceService:

    @staticmethod
    async def mark_attendance(
        db: AsyncSession,
        data: MarkAttendanceRequest,
        marked_by_id: UUID,
        user_role: str = 'teacher',
    ) -> Attendance:
        event = await db.get(Event, data.event_id)
        if not event:
            raise NotFoundException('Event not found')

        if user_role != 'admin' and event.coordinator_id != marked_by_id:
            raise ForbiddenException('You are not the coordinator of this event')

        if not (event.start_date <= data.date <= event.end_date):
            raise ValidationException('Date is outside the event date range')

        reg = await db.execute(
            select(Registration).where(
                Registration.event_id == data.event_id,
                Registration.student_id == data.student_id,
                Registration.status == RegistrationStatus.ACCEPTED,
            )
        )
        if not reg.scalar_one_or_none():
            raise NotFoundException('Student does not have an accepted registration')

        existing = await db.execute(
            select(Attendance).where(
                Attendance.event_id == data.event_id,
                Attendance.student_id == data.student_id,
                Attendance.date == data.date,
            )
        )
        record = existing.scalar_one_or_none()
        if record:
            record.present = data.present
        else:
            record = Attendance(
                event_id=data.event_id,
                student_id=data.student_id,
                date=data.date,
                present=data.present,
                marked_by_id=marked_by_id,
            )
            db.add(record)

        await db.commit()
        await db.refresh(record)
        return record

    @staticmethod
    async def mark_bulk_attendance(
        db: AsyncSession,
        data: BulkAttendanceRequest,
        marked_by_id: UUID,
        user_role: str = 'teacher',
    ) -> dict:
        event = await db.get(Event, data.event_id)
        if not event:
            raise NotFoundException('Event not found')

        if user_role != 'admin' and event.coordinator_id != marked_by_id:
            raise ForbiddenException('You are not the coordinator of this event')

        if not (event.start_date <= data.date <= event.end_date):
            raise ValidationException('Date is outside the event date range')

        result = await db.execute(
            select(Registration.student_id).where(
                Registration.event_id == data.event_id,
                Registration.status == RegistrationStatus.ACCEPTED,
            )
        )
        accepted_ids = {row[0] for row in result.all()}

        valid_records = [r for r in data.records if r.student_id in accepted_ids]

        async with db.begin():
            for rec in valid_records:
                existing = await db.execute(
                    select(Attendance).where(
                        Attendance.event_id == data.event_id,
                        Attendance.student_id == rec.student_id,
                        Attendance.date == data.date,
                    )
                )
                record = existing.scalar_one_or_none()
                if record:
                    record.present = rec.present
                else:
                    record = Attendance(
                        event_id=data.event_id,
                        student_id=rec.student_id,
                        date=data.date,
                        present=rec.present,
                        marked_by_id=marked_by_id,
                    )
                    db.add(record)

        return {'count': len(valid_records)}

    @staticmethod
    async def get_event_attendance(
        db: AsyncSession,
        event_id: UUID,
        user_id: UUID,
        user_role: str,
        date_str: str | None = None,
    ) -> dict:
        event = await db.get(Event, event_id)
        if not event:
            raise NotFoundException('Event not found')

        if user_role != 'admin' and event.coordinator_id != user_id:
            raise ForbiddenException('You are not the coordinator of this event')

        att_date = date.fromisoformat(date_str) if date_str else date.today()

        result = await db.execute(
            select(Registration).where(
                Registration.event_id == event_id,
                Registration.status == RegistrationStatus.ACCEPTED,
            )
        )
        accepted_students = result.scalars().all()

        att_result = await db.execute(
            select(Attendance).where(
                Attendance.event_id == event_id,
                Attendance.date == att_date,
            )
        )
        attendance_records = att_result.scalars().all()
        attendance_map = {a.student_id: a.present for a in attendance_records}

        rows = []
        for reg in accepted_students:
            rows.append({
                'student': {
                    'id': reg.student_id,
                    'name': reg.student.name,
                    'email': reg.student.email,
                },
                'present': attendance_map.get(reg.student_id, None),
            })

        return {'attendance': rows}

    @staticmethod
    async def get_student_attendance(
        db: AsyncSession,
        student_id: UUID,
        user_id: UUID,
        user_role: str,
        page: int = 1,
        limit: int = 20,
    ) -> PaginatedAttendanceResponse:
        if user_role != 'admin' and user_id != student_id:
            raise ForbiddenException('Not authorized to view this student attendance')

        total_q = select(func.count()).select_from(Attendance).where(Attendance.student_id == student_id)
        total_result = await db.execute(total_q)
        total = total_result.scalar() or 0

        query = (
            select(Attendance)
            .where(Attendance.student_id == student_id)
            .offset((page - 1) * limit)
            .limit(limit)
            .order_by(Attendance.date.desc())
        )
        result = await db.execute(query)
        records = result.scalars().all()

        total_pages = 0 if total == 0 else (total + limit - 1) // limit

        data = []
        for rec in records:
            data.append({
                'id': rec.id,
                'event_id': rec.event_id,
                'event_title': rec.event.title,
                'date': rec.date,
                'present': rec.present,
            })

        return PaginatedAttendanceResponse(
            data=data,
            page=page,
            limit=limit,
            total=total,
            total_pages=total_pages,
        )
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/attendance.py
git commit -m "feat: add attendance service with mark, bulk mark, event sheet, student records"
```

---

### Task 3: Create attendance router

**Files:**
- Create: `backend/app/api/v1/attendance.py`

- [ ] **Step 1: Write router implementation**

```python
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.api.deps import get_current_user, RoleChecker
from app.schemas.attendance import (
    MarkAttendanceRequest,
    BulkAttendanceRequest,
    AttendanceResponse,
    AttendanceSheetResponse,
    BulkAttendanceResponse,
    PaginatedAttendanceResponse,
)
from app.services.attendance import AttendanceService

router = APIRouter(prefix='/attendance', tags=['attendance'])


@router.post('/mark', response_model=AttendanceResponse, status_code=201)
async def mark_attendance(
    data: MarkAttendanceRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _: None = Depends(RoleChecker(['teacher', 'admin'])),
):
    record = await AttendanceService.mark_attendance(
        db=db,
        data=data,
        marked_by_id=current_user['id'],
        user_role=current_user['role'],
    )
    return record


@router.post('/bulk', response_model=BulkAttendanceResponse)
async def bulk_attendance(
    data: BulkAttendanceRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _: None = Depends(RoleChecker(['teacher', 'admin'])),
):
    result = await AttendanceService.mark_bulk_attendance(
        db=db,
        data=data,
        marked_by_id=current_user['id'],
        user_role=current_user['role'],
    )
    return result


@router.get('/event/{event_id}', response_model=AttendanceSheetResponse)
async def get_event_attendance(
    event_id: UUID,
    date: str | None = Query(None, description='Date in YYYY-MM-DD format, defaults to today'),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _: None = Depends(RoleChecker(['teacher', 'admin'])),
):
    result = await AttendanceService.get_event_attendance(
        db=db,
        event_id=event_id,
        user_id=current_user['id'],
        user_role=current_user['role'],
        date_str=date,
    )
    return result


@router.get('/student/{student_id}', response_model=PaginatedAttendanceResponse)
async def get_student_attendance(
    student_id: UUID,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _: None = Depends(RoleChecker(['student', 'admin'])),
):
    return await AttendanceService.get_student_attendance(
        db=db,
        student_id=student_id,
        user_id=current_user['id'],
        user_role=current_user['role'],
        page=page,
        limit=limit,
    )
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/api/v1/attendance.py
git commit -m "feat: add attendance router with all 4 endpoints"
```

---

### Task 4: Register attendance router in main.py

**Files:**
- Modify: `backend/app/main.py`

- [ ] **Step 1: Add router registration**

Add import line at top of `backend/app/main.py`:

```python
from app.api.v1.attendance import router as attendance_router
```

Add include line after existing v1 routers:

```python
app.include_router(attendance_router, prefix='/api/v1')
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/main.py
git commit -m "feat: register attendance routes in main.py"
```

---

### Task 5: Integration tests

**Files:**
- Create: `backend/tests/test_attendance.py`
- Modify: `backend/tests/conftest.py` (add test fixtures / data factories if needed)

- [ ] **Step 1: Write integration tests**

```python
import pytest
from httpx import AsyncClient, ASGITransport
from uuid import uuid4, UUID
from datetime import date, timedelta

from app.main import app
from app.db.session import async_session
from app.models.event import Event
from app.models.user import User
from app.models.registration import Registration, RegistrationStatus
from app.models.attendance import Attendance


@pytest.fixture
def coordinator_data():
    return {
        'id': uuid4(),
        'name': 'Dr. Sharma',
        'email': 'sharma@college.edu',
        'role': 'teacher',
        'is_active': True,
    }


@pytest.fixture
def student_data():
    return {
        'id': uuid4(),
        'name': 'Priya Singh',
        'email': 'priya@college.edu',
        'role': 'student',
        'is_active': True,
    }


@pytest.fixture
def event_data(coordinator_data):
    return {
        'id': uuid4(),
        'title': 'Tech Fest',
        'coordinator_id': coordinator_data['id'],
        'start_date': date.today() - timedelta(days=1),
        'end_date': date.today() + timedelta(days=1),
        'status': 'approved',
    }


@pytest.fixture
async def seed_data(coordinator_data, student_data, event_data):
    async with async_session() as db:
        db.add(User(**coordinator_data))
        db.add(User(**student_data))
        db.add(Event(**event_data))
        db.add(Registration(
            event_id=event_data['id'],
            student_id=student_data['id'],
            status=RegistrationStatus.ACCEPTED,
        ))
        await db.commit()


@pytest.mark.asyncio
async def test_mark_attendance_success(seed_data, event_data, student_data, coordinator_data):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url='http://test') as client:
        resp = await client.post(
            '/api/v1/attendance/mark',
            json={
                'event_id': str(event_data['id']),
                'student_id': str(student_data['id']),
                'date': str(date.today()),
                'present': True,
            },
            headers={
                'Authorization': 'Bearer test_token',
                'X-Test-User': coordinator_data['id'],
                'X-Test-Role': 'teacher',
            },
        )
    assert resp.status_code == 201
    data = resp.json()
    assert data['present'] is True
    assert data['student_id'] == str(student_data['id'])


@pytest.mark.asyncio
async def test_mark_attendance_forbidden_non_coordinator(
    seed_data, event_data, student_data,
):
    other_teacher_id = uuid4()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url='http://test') as client:
        resp = await client.post(
            '/api/v1/attendance/mark',
            json={
                'event_id': str(event_data['id']),
                'student_id': str(student_data['id']),
                'date': str(date.today()),
                'present': False,
            },
            headers={
                'Authorization': 'Bearer test_token',
                'X-Test-User': str(other_teacher_id),
                'X-Test-Role': 'teacher',
            },
        )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_mark_attendance_date_outside_range(
    seed_data, event_data, student_data, coordinator_data,
):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url='http://test') as client:
        resp = await client.post(
            '/api/v1/attendance/mark',
            json={
                'event_id': str(event_data['id']),
                'student_id': str(student_data['id']),
                'date': '2020-01-01',
                'present': True,
            },
            headers={
                'Authorization': 'Bearer test_token',
                'X-Test-User': str(coordinator_data['id']),
                'X-Test-Role': 'teacher',
            },
        )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_mark_attendance_not_registered(
    seed_data, event_data, coordinator_data,
):
    unknown_student_id = uuid4()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url='http://test') as client:
        resp = await client.post(
            '/api/v1/attendance/mark',
            json={
                'event_id': str(event_data['id']),
                'student_id': str(unknown_student_id),
                'date': str(date.today()),
                'present': True,
            },
            headers={
                'Authorization': 'Bearer test_token',
                'X-Test-User': str(coordinator_data['id']),
                'X-Test-Role': 'teacher',
            },
        )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_bulk_attendance_success(seed_data, event_data, student_data, coordinator_data):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url='http://test') as client:
        resp = await client.post(
            '/api/v1/attendance/bulk',
            json={
                'event_id': str(event_data['id']),
                'date': str(date.today()),
                'records': [
                    {'student_id': str(student_data['id']), 'present': True},
                ],
            },
            headers={
                'Authorization': 'Bearer test_token',
                'X-Test-User': str(coordinator_data['id']),
                'X-Test-Role': 'teacher',
            },
        )
    assert resp.status_code == 200
    assert resp.json()['count'] == 1


@pytest.mark.asyncio
async def test_bulk_attendance_empty_records(seed_data, event_data, coordinator_data):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url='http://test') as client:
        resp = await client.post(
            '/api/v1/attendance/bulk',
            json={
                'event_id': str(event_data['id']),
                'date': str(date.today()),
                'records': [],
            },
            headers={
                'Authorization': 'Bearer test_token',
                'X-Test-User': str(coordinator_data['id']),
                'X-Test-Role': 'teacher',
            },
        )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_get_event_attendance(seed_data, event_data, student_data, coordinator_data):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url='http://test') as client:
        resp = await client.get(
            f'/api/v1/attendance/event/{event_data["id"]}',
            headers={
                'Authorization': 'Bearer test_token',
                'X-Test-User': str(coordinator_data['id']),
                'X-Test-Role': 'teacher',
            },
        )
    assert resp.status_code == 200
    body = resp.json()
    assert 'attendance' in body
    assert len(body['attendance']) == 1
    assert body['attendance'][0]['student']['id'] == str(student_data['id'])


@pytest.mark.asyncio
async def test_get_event_attendance_admin_bypass(
    seed_data, event_data, student_data,
):
    admin_id = uuid4()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url='http://test') as client:
        resp = await client.get(
            f'/api/v1/attendance/event/{event_data["id"]}',
            headers={
                'Authorization': 'Bearer test_token',
                'X-Test-User': str(admin_id),
                'X-Test-Role': 'admin',
            },
        )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_get_event_attendance_forbidden(
    seed_data, event_data,
):
    other_teacher_id = uuid4()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url='http://test') as client:
        resp = await client.get(
            f'/api/v1/attendance/event/{event_data["id"]}',
            headers={
                'Authorization': 'Bearer test_token',
                'X-Test-User': str(other_teacher_id),
                'X-Test-Role': 'teacher',
            },
        )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_get_student_attendance_own(seed_data, student_data):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url='http://test') as client:
        resp = await client.get(
            f'/api/v1/attendance/student/{student_data["id"]}',
            headers={
                'Authorization': 'Bearer test_token',
                'X-Test-User': str(student_data['id']),
                'X-Test-Role': 'student',
            },
        )
    assert resp.status_code == 200
    body = resp.json()
    assert 'data' in body
    assert 'page' in body
    assert 'total_pages' in body


@pytest.mark.asyncio
async def test_get_student_attendance_admin(seed_data, student_data):
    admin_id = uuid4()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url='http://test') as client:
        resp = await client.get(
            f'/api/v1/attendance/student/{student_data["id"]}',
            headers={
                'Authorization': 'Bearer test_token',
                'X-Test-User': str(admin_id),
                'X-Test-Role': 'admin',
            },
        )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_get_student_attendance_forbidden(seed_data, student_data):
    other_student_id = uuid4()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url='http://test') as client:
        resp = await client.get(
            f'/api/v1/attendance/student/{student_data["id"]}',
            headers={
                'Authorization': 'Bearer test_token',
                'X-Test-User': str(other_student_id),
                'X-Test-Role': 'student',
            },
        )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_attendance_requires_auth(seed_data, event_data):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url='http://test') as client:
        resp = await client.post(
            '/api/v1/attendance/mark',
            json={
                'event_id': str(event_data['id']),
                'student_id': str(uuid4()),
                'date': str(date.today()),
                'present': True,
            },
        )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_attendance_upsert_updates(seed_data, event_data, student_data, coordinator_data):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url='http://test') as client:
        resp1 = await client.post(
            '/api/v1/attendance/mark',
            json={
                'event_id': str(event_data['id']),
                'student_id': str(student_data['id']),
                'date': str(date.today()),
                'present': True,
            },
            headers={
                'Authorization': 'Bearer test_token',
                'X-Test-User': str(coordinator_data['id']),
                'X-Test-Role': 'teacher',
            },
        )
        assert resp1.status_code == 201
        assert resp1.json()['present'] is True

        resp2 = await client.post(
            '/api/v1/attendance/mark',
            json={
                'event_id': str(event_data['id']),
                'student_id': str(student_data['id']),
                'date': str(date.today()),
                'present': False,
            },
            headers={
                'Authorization': 'Bearer test_token',
                'X-Test-User': str(coordinator_data['id']),
                'X-Test-Role': 'teacher',
            },
        )
        assert resp2.status_code == 201
        assert resp2.json()['present'] is False


@pytest.mark.asyncio
async def test_get_student_attendance_pagination(seed_data, event_data, student_data, coordinator_data):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url='http://test') as client:
        resp = await client.get(
            f'/api/v1/attendance/student/{student_data["id"]}?page=1&limit=10',
            headers={
                'Authorization': 'Bearer test_token',
                'X-Test-User': str(student_data['id']),
                'X-Test-Role': 'student',
            },
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body['page'] == 1
    assert body['limit'] == 10
```

- [ ] **Step 2: Run tests**

```bash
cd backend && pytest tests/test_attendance.py -v --asyncio-mode=auto
```

Expected: ALL PASS

- [ ] **Step 3: Run full test suite**

```bash
cd backend && pytest -v --asyncio-mode=auto
```

Expected: All tests PASS

- [ ] **Step 4: Run type check**

```bash
cd backend && mypy app/ tests/ --ignore-missing-imports
```

Expected: No errors

- [ ] **Step 5: Commit**

```bash
git add backend/tests/test_attendance.py
git commit -m "test: add integration tests for attendance module"
```

---

## Spec Coverage Check

| Spec Requirement | File | Status |
|---|---|---|
| POST /api/v1/attendance/mark — mark single (teacher coordinator, upsert, 201) | schemas/attendance.py, services/attendance.py, api/v1/attendance.py | Done |
| POST /api/v1/attendance/bulk — bulk mark (async transaction, atomic, returns count, 200) | schemas/attendance.py, services/attendance.py, api/v1/attendance.py | Done |
| GET /api/v1/attendance/event/:event_id — attendance sheet (coordinator/admin, optional date, all accepted students + status, 200) | services/attendance.py, api/v1/attendance.py | Done |
| GET /api/v1/attendance/student/:student_id — student records (own or admin, paginated, 200) | services/attendance.py, api/v1/attendance.py | Done |
| Validation: teacher must be coordinator of event | services/attendance.py | Done |
| Validation: student must have accepted registration | services/attendance.py | Done |
| Validation: date must be within event range | services/attendance.py | Done |
| Upsert creates or updates attendance record | services/attendance.py, test | Done |
| Bulk uses async transaction for atomicity | services/attendance.py | Done |
| Bulk skips records without accepted registration | services/attendance.py | Done |
| Admin can bypass coordinator check | services/attendance.py | Done |
| Admin can view any student attendance | services/attendance.py | Done |
| Date defaults to today for event attendance sheet | services/attendance.py | Done |

## Placeholder Scan

No placeholders ("TODO", "implement later", "fill in details") found. Every code block contains complete, runnable code with exact file paths, imports, and test assertions. All error handling is explicit.

## Type Consistency Check

- `AttendanceService.mark_attendance(db, data: MarkAttendanceRequest, marked_by_id: UUID, user_role: str = 'teacher') -> Attendance` — returns SQLAlchemy model instance, FastAPI serialises via `response_model=AttendanceResponse`
- `AttendanceService.mark_bulk_attendance(db, data: BulkAttendanceRequest, marked_by_id: UUID, user_role: str = 'teacher') -> dict` — returns `{'count': int}`, serialised via `BulkAttendanceResponse`
- `AttendanceService.get_event_attendance(db, event_id: UUID, user_id: UUID, user_role: str, date_str: str | None = None) -> dict` — returns `{'attendance': [{'student': {...}, 'present': bool|None}]}`, serialised via `AttendanceSheetResponse`
- `AttendanceService.get_student_attendance(db, student_id: UUID, user_id: UUID, user_role: str, page: int = 1, limit: int = 20) -> PaginatedAttendanceResponse` — returns Pydantic paginated model
- `MarkAttendanceRequest` fields: `event_id: UUID, student_id: UUID, date: date, present: bool` — matches API spec
- `BulkAttendanceRequest` fields: `event_id: UUID, date: date, records: list[BulkAttendanceRecord]` — matches API spec
- `get_event_attendance` returns `{'attendance': [...]}` — matches API spec
- `get_student_attendance` returns `PaginatedAttendanceResponse` with `data, page, limit, total, total_pages` — matches API spec
- Role strings: `'teacher'`, `'admin'`, `'student'` — consistent across all service functions and router dependencies
- `response_model` annotations in router exactly match schema types — ensures OpenAPI correctness
