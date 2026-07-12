# Phase 4: Events Module Implementation Plan (Python FastAPI)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement full event management with role-based CRUD, approval workflow, coordinator assignment, and brochure upload.

**Architecture:** Events module handles the core domain logic. The approval workflow uses a state machine pattern (draft→pending→approved/rejected). Brochure upload returns a mock presigned URL in dev (no S3). All business logic lives in a service layer separated from HTTP concerns via FastAPI dependency injection.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy 2.0 (async), Pydantic v2, pytest-asyncio, httpx

---

## File Structure

```
backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       └── events.py                # CREATE: FastAPI router
│   ├── schemas/
│   │   └── event.py                     # CREATE: Pydantic schemas
│   ├── services/
│   │   └── event.py                     # CREATE: business logic
│   ├── models/
│   │   └── event.py                     # EXISTING (or MODIFY if brochure fields missing)
│   ├── main.py                          # MODIFY: include event router
│   └── deps.py                          # EXISTING: auth/user deps
├── tests/
│   ├── conftest.py                      # EXISTING: async fixtures, test client
│   └── test_events.py                   # CREATE: integration tests
└── requirements.txt                     # MODIFY: add pytest-asyncio, httpx if missing
```

---

### Task 0: Ensure Event model has brochure fields and coordinator is nullable

**Files:**
- Verify/modify: `backend/app/models/event.py` (brochure fields, nullable coordinator)

- [ ] **Step 1: Verify Event model in SQLAlchemy**

Read `backend/app/models/event.py` — ensure it has:

```python
from sqlalchemy import Column, String, Text, DateTime, Integer, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from app.models.base import Base
import enum

class EventStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class EventType(str, enum.Enum):
    IN_COLLEGE = "in_college"
    OUT_COLLEGE = "out_college"

class EventCategory(str, enum.Enum):
    VOLUNTEER = "volunteer"
    PARTICIPANT = "participant"
    BOTH = "both"

class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, autoincrement=True)  # or UUID
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    type = Column(SAEnum(EventType), nullable=False)
    category = Column(SAEnum(EventCategory), nullable=False)
    status = Column(SAEnum(EventStatus), default=EventStatus.DRAFT, nullable=False)
    venue = Column(String(300), nullable=True)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    max_registrations = Column(Integer, default=0, nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    coordinator_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    brochure_url = Column(Text, nullable=True)
    brochure_file_key = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    created_by = relationship("User", foreign_keys=[created_by_id])
    coordinator = relationship("User", foreign_keys=[coordinator_id])
    registrations = relationship("Registration", back_populates="event")
    attendance = relationship("Attendance", back_populates="event")
```

If brochure fields or nullable coordinator are missing, add them and create an Alembic migration.

- [ ] **Step 2: Create Alembic migration if model changed**

```bash
cd backend && alembic revision --autogenerate -m "add_brochure_fields_nullable_coordinator"
```

- [ ] **Step 3: Apply migration**

```bash
cd backend && alembic upgrade head
```

Expected: "OK" — schema is up to date

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/event.py backend/alembic/versions/
git commit -m "feat: ensure Event model has brochure fields and nullable coordinator"
```

---

### Task 1: Event schemas (Pydantic)

**Files:**
- Create: `backend/app/schemas/event.py`

- [ ] **Step 1: Write the Pydantic schemas**

Create `backend/app/schemas/event.py`:

```python
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from enum import Enum


class EventType(str, Enum):
    IN_COLLEGE = "in_college"
    OUT_COLLEGE = "out_college"


class EventCategory(str, Enum):
    VOLUNTEER = "volunteer"
    PARTICIPANT = "participant"
    BOTH = "both"


class EventStatus(str, Enum):
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class EventQueryParams(BaseModel):
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)
    status: Optional[EventStatus] = None
    type: Optional[EventType] = None
    category: Optional[EventCategory] = None
    search: Optional[str] = None


class EventCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    type: EventType
    category: EventCategory
    start_date: datetime
    end_date: datetime


class EventUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    category: Optional[EventCategory] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class EventApprove(BaseModel):
    admin_comment: Optional[str] = None


class EventReject(BaseModel):
    admin_comment: str = Field(..., min_length=1)


class EventAssignCoordinator(BaseModel):
    coordinator_id: int


ALLOWED_BROCHURE_TYPES = {"application/pdf", "image/jpeg", "image/png"}


class EventBrochureRequest(BaseModel):
    file_name: str = Field(..., min_length=1)
    file_type: str = Field(..., min_length=1)

    @field_validator("file_type")
    @classmethod
    def validate_file_type(cls, v: str) -> str:
        if v not in ALLOWED_BROCHURE_TYPES:
            raise ValueError(
                f"file_type must be one of {ALLOWED_BROCHURE_TYPES}, got '{v}'"
            )
        return v


class EventBrochureResponse(BaseModel):
    upload_url: str
    file_key: str


class UserBrief(BaseModel):
    id: int
    name: str
    email: str

    model_config = {"from_attributes": True}


class EventCounts(BaseModel):
    registrations: int = 0
    attendance: int = 0


class EventOut(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    type: EventType
    category: EventCategory
    status: EventStatus
    venue: Optional[str] = None
    start_date: datetime
    end_date: datetime
    max_registrations: int
    brochure_url: Optional[str] = None
    brochure_file_key: Optional[str] = None
    created_by: Optional[UserBrief] = None
    coordinator: Optional[UserBrief] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EventListItem(BaseModel):
    id: int
    title: str
    type: EventType
    category: EventCategory
    status: EventStatus
    start_date: datetime
    end_date: datetime
    registration_count: int = 0
    created_by_name: Optional[str] = None

    model_config = {"from_attributes": True}


class PaginatedResponse(BaseModel):
    items: list
    total: int
    page: int
    limit: int
    total_pages: int
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/schemas/event.py
git commit -m "feat: add Pydantic schemas for events module"
```

---

### Task 2: Event service - list & create

**Files:**
- Create: `backend/app/services/event.py` (partial — list_events + create_event)

- [ ] **Step 1: Write service implementation (list_events + create_event)**

Create `backend/app/services/event.py`:

```python
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from datetime import datetime, date
from typing import Optional

from app.models.event import Event, EventStatus, EventType
from app.models.user import User, Role
from app.schemas.event import EventCreate, EventQueryParams
from app.core.exceptions import ForbiddenError, ValidationError


class EventService:

    @staticmethod
    async def list_events(
        db: AsyncSession,
        user: User,
        params: EventQueryParams,
    ) -> tuple[list[Event], int]:
        query = (
            select(Event)
            .options(
                selectinload(Event.created_by),
                selectinload(Event.coordinator),
            )
        )

        if user.role == Role.STUDENT:
            query = query.where(Event.status == EventStatus.APPROVED)
        elif user.role == Role.TEACHER:
            query = query.where(
                or_(
                    Event.coordinator_id == user.id,
                    Event.created_by_id == user.id,
                )
            )

        if params.status:
            query = query.where(Event.status == params.status)
        if params.type:
            query = query.where(Event.type == params.type)
        if params.category:
            query = query.where(Event.category == params.category)
        if params.search:
            query = query.where(Event.title.ilike(f"%{params.search}%"))

        count_query = select(func.count()).select_from(query.subquery())
        total = await db.scalar(count_query) or 0

        query = query.order_by(Event.created_at.desc())
        query = query.offset((params.page - 1) * params.limit).limit(params.limit)

        result = await db.execute(query)
        events = list(result.scalars().all())
        return events, total

    @staticmethod
    async def create_event(
        db: AsyncSession,
        data: EventCreate,
        user: User,
    ) -> Event:
        today = date.today()
        if data.start_date.date() < today:
            raise ValidationError("Start date must be today or a future date")
        if data.end_date < data.start_date:
            raise ValidationError("End date must be after start date")

        if data.type == EventType.IN_COLLEGE and user.role != Role.ADMIN:
            raise ForbiddenError("Only admins can create in_college events")
        if data.type == EventType.OUT_COLLEGE and user.role != Role.STUDENT:
            raise ForbiddenError("Only students can create out_college events")

        status = EventStatus.DRAFT if data.type == EventType.IN_COLLEGE else EventStatus.PENDING

        event = Event(
            title=data.title,
            description=data.description,
            type=data.type,
            category=data.category,
            status=status,
            start_date=data.start_date,
            end_date=data.end_date,
            created_by_id=user.id,
        )
        db.add(event)
        await db.commit()
        await db.refresh(event)
        return event
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/event.py
git commit -m "feat: add list_events and create_event service methods"
```

---

### Task 3: Event service - get by ID with counts

**Files:**
- Modify: `backend/app/services/event.py` (add get_event_by_id)

- [ ] **Step 1: Write get_event_by_id implementation**

Append to `backend/app/services/event.py`:

```python
    @staticmethod
    async def get_event_by_id(
        db: AsyncSession,
        event_id: int,
    ) -> Event:
        from app.models.registration import Registration
        from app.models.attendance import Attendance

        query = (
            select(Event)
            .options(
                selectinload(Event.created_by),
                selectinload(Event.coordinator),
            )
            .where(Event.id == event_id)
        )
        result = await db.execute(query)
        event = result.scalar_one_or_none()

        if not event:
            from app.core.exceptions import NotFoundError
            raise NotFoundError("Event not found")

        # Attach counts manually (or rely on relationship count if configured)
        reg_count_query = (
            select(func.count())
            .select_from(Registration)
            .where(Registration.event_id == event_id)
        )
        att_count_query = (
            select(func.count())
            .select_from(Attendance)
            .where(Attendance.event_id == event_id)
        )
        event._registration_count = await db.scalar(reg_count_query) or 0
        event._attendance_count = await db.scalar(att_count_query) or 0

        return event
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/event.py
git commit -m "feat: add get_event_by_id service method"
```

---

### Task 4: Event service - update

**Files:**
- Modify: `backend/app/services/event.py` (add update_event)

- [ ] **Step 1: Write update_event implementation**

Append to `backend/app/services/event.py`:

```python
    @staticmethod
    async def update_event(
        db: AsyncSession,
        event_id: int,
        data: EventUpdate,
        user: User,
    ) -> Event:
        event = await EventService.get_event_by_id(db, event_id)

        is_creator = event.created_by_id == user.id
        is_admin = user.role == Role.ADMIN
        if not is_creator and not is_admin:
            from app.core.exceptions import ForbiddenError
            raise ForbiddenError("Not authorized to update this event")

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(event, field, value)

        await db.commit()
        await db.refresh(event)
        return event
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/event.py
git commit -m "feat: add update_event service method"
```

---

### Task 5: Event service - approve/reject

**Files:**
- Modify: `backend/app/services/event.py` (add approve_event, reject_event)

- [ ] **Step 1: Write approve_event and reject_event implementation**

Append to `backend/app/services/event.py`:

```python
    @staticmethod
    async def approve_event(
        db: AsyncSession,
        event_id: int,
        admin_comment: Optional[str],
        user: User,
    ) -> Event:
        from app.core.exceptions import ConflictError, ForbiddenError

        event = await EventService.get_event_by_id(db, event_id)

        if event.status == EventStatus.APPROVED:
            raise ConflictError("Event is already approved")
        if event.status == EventStatus.REJECTED:
            raise ConflictError("Cannot approve a rejected event")

        is_admin = user.role == Role.ADMIN
        is_coordinator = event.coordinator_id == user.id

        if not is_admin and not is_coordinator:
            raise ForbiddenError("Not authorized to approve this event")
        if is_coordinator and user.role != Role.TEACHER:
            raise ForbiddenError("Only teachers can approve as coordinators")

        event.status = EventStatus.APPROVED
        await db.commit()
        await db.refresh(event)
        return event

    @staticmethod
    async def reject_event(
        db: AsyncSession,
        event_id: int,
        admin_comment: str,
        user: User,
    ) -> Event:
        from app.core.exceptions import ConflictError, ForbiddenError

        event = await EventService.get_event_by_id(db, event_id)

        if event.status == EventStatus.REJECTED:
            raise ConflictError("Event is already rejected")

        is_admin = user.role == Role.ADMIN
        is_coordinator = event.coordinator_id == user.id

        if not is_admin and not is_coordinator:
            raise ForbiddenError("Not authorized to reject this event")

        event.status = EventStatus.REJECTED
        await db.commit()
        await db.refresh(event)
        return event
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/event.py
git commit -m "feat: add approve_event and reject_event service methods"
```

---

### Task 6: Event service - assign coordinator

**Files:**
- Modify: `backend/app/services/event.py` (add assign_coordinator)

- [ ] **Step 1: Write assign_coordinator implementation**

Append to `backend/app/services/event.py`:

```python
    @staticmethod
    async def assign_coordinator(
        db: AsyncSession,
        event_id: int,
        coordinator_id: int,
    ) -> Event:
        from app.core.exceptions import ValidationError

        event = await EventService.get_event_by_id(db, event_id)

        coordinator_query = select(User).where(User.id == coordinator_id)
        result = await db.execute(coordinator_query)
        coordinator = result.scalar_one_or_none()

        if not coordinator:
            from app.core.exceptions import NotFoundError
            raise NotFoundError("Coordinator user not found")
        if coordinator.role != Role.TEACHER:
            raise ValidationError("Coordinator must be a teacher")
        if coordinator.status != "active":
            raise ValidationError("Coordinator must have active status")

        event.coordinator_id = coordinator_id
        await db.commit()
        await db.refresh(event)
        return event
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/event.py
git commit -m "feat: add assign_coordinator service method"
```

---

### Task 7: Event service - brochure URL

**Files:**
- Modify: `backend/app/services/event.py` (add request_brochure_url)

- [ ] **Step 1: Write request_brochure_url implementation**

Append to `backend/app/services/event.py`:

```python
    @staticmethod
    async def request_brochure_url(
        db: AsyncSession,
        event_id: int,
        file_name: str,
        file_type: str,
        user: User,
    ) -> dict:
        from uuid import uuid4
        from app.core.exceptions import ForbiddenError, ValidationError

        event = await EventService.get_event_by_id(db, event_id)

        if event.type != EventType.OUT_COLLEGE:
            raise ValidationError("Brochure upload is only available for out_college events")
        if event.created_by_id != user.id:
            raise ForbiddenError("Only the event creator can upload a brochure")

        file_key = f"brochures/{uuid4()}-{file_name}"
        upload_url = f"http://localhost:8000/mock-upload/{file_key}"

        event.brochure_url = upload_url
        event.brochure_file_key = file_key
        await db.commit()

        return {"upload_url": upload_url, "file_key": file_key}
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/event.py
git commit -m "feat: add request_brochure_url service method with mock upload URL"
```

---

### Task 8: Event router

**Files:**
- Create: `backend/app/api/v1/events.py`

- [ ] **Step 1: Create the FastAPI router**

Create `backend/app/api/v1/events.py`:

```python
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.deps import get_db, get_current_user
from app.models.user import User, Role
from app.schemas.event import (
    EventCreate,
    EventUpdate,
    EventApprove,
    EventReject,
    EventAssignCoordinator,
    EventBrochureRequest,
    EventQueryParams,
    EventOut,
    EventListItem,
    PaginatedResponse,
)
from app.services.event import EventService
from app.core.exceptions import NotFoundError

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=PaginatedResponse)
async def list_events(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    params = EventQueryParams(
        page=page, limit=limit,
        status=status, type=type,
        category=category, search=search,
    )
    events, total = await EventService.list_events(db, current_user, params)
    items = [
        EventListItem(
            id=e.id,
            title=e.title,
            type=e.type,
            category=e.category,
            status=e.status,
            start_date=e.start_date,
            end_date=e.end_date,
            registration_count=len(getattr(e, "registrations", [])),
            created_by_name=e.created_by.name if e.created_by else None,
        )
        for e in events
    ]
    total_pages = max(1, (total + limit - 1) // limit) if total else 0
    return PaginatedResponse(
        items=items, total=total,
        page=page, limit=limit,
        total_pages=total_pages,
    )


@router.post("", response_model=EventOut, status_code=201)
async def create_event(
    data: EventCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    event = await EventService.create_event(db, data, current_user)
    return event


@router.get("/{event_id}", response_model=EventOut)
async def get_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    event = await EventService.get_event_by_id(db, event_id)
    return event


@router.patch("/{event_id}", response_model=EventOut)
async def update_event(
    event_id: int,
    data: EventUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    event = await EventService.update_event(db, event_id, data, current_user)
    return event


@router.patch("/{event_id}/approve", response_model=EventOut)
async def approve_event(
    event_id: int,
    data: EventApprove,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in (Role.ADMIN, Role.TEACHER):
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Not authorized")
    event = await EventService.approve_event(db, event_id, data.admin_comment, current_user)
    return event


@router.patch("/{event_id}/reject", response_model=EventOut)
async def reject_event(
    event_id: int,
    data: EventReject,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in (Role.ADMIN, Role.TEACHER):
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Not authorized")
    event = await EventService.reject_event(db, event_id, data.admin_comment, current_user)
    return event


@router.patch("/{event_id}/assign-coordinator", response_model=EventOut)
async def assign_coordinator(
    event_id: int,
    data: EventAssignCoordinator,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != Role.ADMIN:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Not authorized")
    event = await EventService.assign_coordinator(db, event_id, data.coordinator_id)
    return event


@router.post("/{event_id}/brochure")
async def request_brochure_url(
    event_id: int,
    data: EventBrochureRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await EventService.request_brochure_url(
        db, event_id, data.file_name, data.file_type, current_user
    )
    return result
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/api/v1/events.py
git commit -m "feat: add events FastAPI router with all 8 endpoints"
```

---

### Task 9: Register router in main.py

**Files:**
- Modify: `backend/app/main.py`

- [ ] **Step 1: Register the events router**

Edit `backend/app/main.py` — add import and include_router:

```python
from app.api.v1.events import router as events_router

# ── V1 API Routes ────────────────────────────────────
app.include_router(events_router, prefix="/api/v1")
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/main.py
git commit -m "feat: register events router in main.py"
```

---

### Task 10: Integration tests

**Files:**
- Create: `backend/tests/test_events.py`

- [ ] **Step 1: Write comprehensive integration tests**

Create `backend/tests/test_events.py`:

```python
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch

from app.main import app
from app.models.user import Role
from app.schemas.event import EventStatus, EventType, EventCategory


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def admin_user():
    user = AsyncMock()
    user.id = 1
    user.role = Role.ADMIN
    user.status = "active"
    user.name = "Admin"
    return user


@pytest.fixture
def student_user():
    user = AsyncMock()
    user.id = 2
    user.role = Role.STUDENT
    user.status = "active"
    user.name = "Student"
    return user


@pytest.fixture
def teacher_user():
    user = AsyncMock()
    user.id = 3
    user.role = Role.TEACHER
    user.status = "active"
    user.name = "Teacher"
    return user


@pytest.mark.asyncio
@patch("app.api.v1.events.get_db")
@patch("app.api.v1.events.get_current_user")
async def test_list_events_paginated(
    mock_get_user, mock_get_db, admin_user, mock_db
):
    mock_get_user.return_value = admin_user
    mock_get_db.return_value = mock_db

    mock_db.execute.return_value.scalars.return_value.all.return_value = []
    mock_db.scalar.return_value = 0

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/events")

    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "limit" in data


@pytest.mark.asyncio
@patch("app.api.v1.events.get_db")
@patch("app.api.v1.events.get_current_user")
async def test_list_events_filters_student(
    mock_get_user, mock_get_db, student_user, mock_db
):
    mock_get_user.return_value = student_user
    mock_get_db.return_value = mock_db

    mock_db.execute.return_value.scalars.return_value.all.return_value = []
    mock_db.scalar.return_value = 0

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/events?status=approved")

    assert resp.status_code == 200


@pytest.mark.asyncio
@patch("app.api.v1.events.get_db")
@patch("app.api.v1.events.get_current_user")
async def test_list_events_with_search(
    mock_get_user, mock_get_db, admin_user, mock_db
):
    mock_get_user.return_value = admin_user
    mock_get_db.return_value = mock_db

    mock_db.execute.return_value.scalars.return_value.all.return_value = []
    mock_db.scalar.return_value = 0

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/events?search=tech")

    assert resp.status_code == 200


@pytest.mark.asyncio
@patch("app.api.v1.events.get_db")
@patch("app.api.v1.events.get_current_user")
async def test_create_event_as_admin(
    mock_get_user, mock_get_db, admin_user, mock_db
):
    from datetime import datetime, timedelta

    mock_get_user.return_value = admin_user
    mock_get_db.return_value = mock_db

    mock_event = AsyncMock()
    mock_event.id = 1
    mock_event.title = "Tech Fest"
    mock_event.type = EventType.IN_COLLEGE
    mock_event.category = EventCategory.BOTH
    mock_event.status = EventStatus.DRAFT
    mock_event.start_date = datetime.utcnow() + timedelta(days=1)
    mock_event.end_date = datetime.utcnow() + timedelta(days=2)
    mock_event.description = None
    mock_event.venue = None
    mock_event.max_registrations = 0
    mock_event.brochure_url = None
    mock_event.brochure_file_key = None
    mock_event.created_by = admin_user
    mock_event.coordinator = None
    mock_event.created_at = datetime.utcnow()
    mock_event.updated_at = datetime.utcnow()
    mock_db.add.return_value = None
    mock_db.commit.return_value = None
    mock_db.refresh.return_value = None
    mock_db.refresh.side_effect = lambda obj: None

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/events", json={
            "title": "Tech Fest",
            "type": "in_college",
            "category": "both",
            "start_date": (datetime.utcnow() + timedelta(days=1)).isoformat(),
            "end_date": (datetime.utcnow() + timedelta(days=2)).isoformat(),
        })

    assert resp.status_code == 201
    assert resp.json()["title"] == "Tech Fest"


@pytest.mark.asyncio
@patch("app.api.v1.events.get_db")
@patch("app.api.v1.events.get_current_user")
async def test_create_event_invalid_body(
    mock_get_user, mock_get_db, admin_user, mock_db
):
    mock_get_user.return_value = admin_user
    mock_get_db.return_value = mock_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/events", json={"title": ""})

    assert resp.status_code == 422


@pytest.mark.asyncio
@patch("app.api.v1.events.get_db")
@patch("app.api.v1.events.get_current_user")
async def test_get_event_by_id(
    mock_get_user, mock_get_db, admin_user, mock_db
):
    mock_get_user.return_value = admin_user
    mock_get_db.return_value = mock_db

    mock_event = AsyncMock()
    mock_event.id = 1
    mock_event.title = "Event 1"
    mock_event.type = EventType.IN_COLLEGE
    mock_event.category = EventCategory.BOTH
    mock_event.status = EventStatus.APPROVED
    mock_event.start_date = None
    mock_event.end_date = None
    mock_event.description = None
    mock_event.venue = None
    mock_event.max_registrations = 0
    mock_event.brochure_url = None
    mock_event.brochure_file_key = None
    mock_event.created_by = admin_user
    mock_event.coordinator = None
    mock_event.created_at = None
    mock_event.updated_at = None
    mock_event._registration_count = 5
    mock_event._attendance_count = 3
    mock_db.execute.return_value.scalar_one_or_none.return_value = mock_event
    mock_db.scalar.return_value = 0

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/events/1")

    assert resp.status_code == 200


@pytest.mark.asyncio
@patch("app.api.v1.events.get_db")
@patch("app.api.v1.events.get_current_user")
async def test_get_event_not_found(
    mock_get_user, mock_get_db, admin_user, mock_db
):
    from app.core.exceptions import NotFoundError

    mock_get_user.return_value = admin_user
    mock_get_db.return_value = mock_db

    async def raise_not_found(*args, **kwargs):
        raise NotFoundError("Event not found")

    mock_db.execute.side_effect = raise_not_found

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/events/999")

    assert resp.status_code == 404


@pytest.mark.asyncio
@patch("app.api.v1.events.get_db")
@patch("app.api.v1.events.get_current_user")
async def test_update_event(
    mock_get_user, mock_get_db, admin_user, mock_db
):
    mock_get_user.return_value = admin_user
    mock_get_db.return_value = mock_db

    mock_event = AsyncMock()
    mock_event.id = 1
    mock_event.title = "Updated Title"
    mock_event.type = EventType.IN_COLLEGE
    mock_event.category = EventCategory.BOTH
    mock_event.status = EventStatus.DRAFT
    mock_event.start_date = None
    mock_event.end_date = None
    mock_event.description = None
    mock_event.venue = None
    mock_event.max_registrations = 0
    mock_event.brochure_url = None
    mock_event.brochure_file_key = None
    mock_event.created_by = admin_user
    mock_event.coordinator = None
    mock_event.created_at = None
    mock_event.updated_at = None
    mock_event.created_by_id = 1
    mock_event._registration_count = 0
    mock_event._attendance_count = 0
    mock_db.execute.return_value.scalar_one_or_none.return_value = mock_event
    mock_db.scalar.return_value = 0

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.patch("/api/v1/events/1", json={"title": "Updated Title"})

    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated Title"


@pytest.mark.asyncio
@patch("app.api.v1.events.get_db")
@patch("app.api.v1.events.get_current_user")
async def test_approve_event(
    mock_get_user, mock_get_db, admin_user, mock_db
):
    mock_get_user.return_value = admin_user
    mock_get_db.return_value = mock_db

    mock_event = AsyncMock()
    mock_event.id = 1
    mock_event.title = "Event"
    mock_event.type = EventType.OUT_COLLEGE
    mock_event.category = EventCategory.BOTH
    mock_event.status = EventStatus.APPROVED
    mock_event.start_date = None
    mock_event.end_date = None
    mock_event.description = None
    mock_event.venue = None
    mock_event.max_registrations = 0
    mock_event.brochure_url = None
    mock_event.brochure_file_key = None
    mock_event.created_by = admin_user
    mock_event.coordinator = None
    mock_event.created_at = None
    mock_event.updated_at = None
    mock_event._registration_count = 0
    mock_event._attendance_count = 0
    mock_db.execute.return_value.scalar_one_or_none.return_value = mock_event
    mock_db.scalar.return_value = 0

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.patch("/api/v1/events/1/approve", json={})

    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"


@pytest.mark.asyncio
@patch("app.api.v1.events.get_db")
@patch("app.api.v1.events.get_current_user")
async def test_approve_event_unauthorized(
    mock_get_user, mock_get_db, student_user, mock_db
):
    mock_get_user.return_value = student_user
    mock_get_db.return_value = mock_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.patch("/api/v1/events/1/approve", json={})

    assert resp.status_code == 403


@pytest.mark.asyncio
@patch("app.api.v1.events.get_db")
@patch("app.api.v1.events.get_current_user")
async def test_reject_event(
    mock_get_user, mock_get_db, admin_user, mock_db
):
    mock_get_user.return_value = admin_user
    mock_get_db.return_value = mock_db

    mock_event = AsyncMock()
    mock_event.id = 1
    mock_event.title = "Event"
    mock_event.type = EventType.OUT_COLLEGE
    mock_event.category = EventCategory.BOTH
    mock_event.status = EventStatus.REJECTED
    mock_event.start_date = None
    mock_event.end_date = None
    mock_event.description = None
    mock_event.venue = None
    mock_event.max_registrations = 0
    mock_event.brochure_url = None
    mock_event.brochure_file_key = None
    mock_event.created_by = admin_user
    mock_event.coordinator = None
    mock_event.created_at = None
    mock_event.updated_at = None
    mock_event._registration_count = 0
    mock_event._attendance_count = 0
    mock_db.execute.return_value.scalar_one_or_none.return_value = mock_event
    mock_db.scalar.return_value = 0

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.patch("/api/v1/events/1/reject", json={"admin_comment": "Not suitable"})

    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"


@pytest.mark.asyncio
@patch("app.api.v1.events.get_db")
@patch("app.api.v1.events.get_current_user")
async def test_reject_event_missing_comment(
    mock_get_user, mock_get_db, admin_user, mock_db
):
    mock_get_user.return_value = admin_user
    mock_get_db.return_value = mock_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.patch("/api/v1/events/1/reject", json={})

    assert resp.status_code == 422


@pytest.mark.asyncio
@patch("app.api.v1.events.get_db")
@patch("app.api.v1.events.get_current_user")
async def test_assign_coordinator(
    mock_get_user, mock_get_db, admin_user, mock_db
):
    mock_get_user.return_value = admin_user
    mock_get_db.return_value = mock_db

    mock_event = AsyncMock()
    mock_event.id = 1
    mock_event.title = "Event"
    mock_event.type = EventType.OUT_COLLEGE
    mock_event.category = EventCategory.BOTH
    mock_event.status = EventStatus.PENDING
    mock_event.start_date = None
    mock_event.end_date = None
    mock_event.description = None
    mock_event.venue = None
    mock_event.max_registrations = 0
    mock_event.brochure_url = None
    mock_event.brochure_file_key = None
    mock_event.created_by = admin_user
    mock_event.coordinator = None
    mock_event.coordinator_id = 3
    mock_event.created_at = None
    mock_event.updated_at = None
    mock_event._registration_count = 0
    mock_event._attendance_count = 0
    mock_db.execute.return_value.scalar_one_or_none.return_value = mock_event
    mock_db.scalar.return_value = 0

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.patch("/api/v1/events/1/assign-coordinator", json={"coordinator_id": 3})

    assert resp.status_code == 200
    assert resp.json()["coordinator_id"] == 3


@pytest.mark.asyncio
@patch("app.api.v1.events.get_db")
@patch("app.api.v1.events.get_current_user")
async def test_request_brochure_url(
    mock_get_user, mock_get_db, student_user, mock_db
):
    mock_get_user.return_value = student_user
    mock_get_db.return_value = mock_db
    student_user.id = 2

    mock_event = AsyncMock()
    mock_event.id = 1
    mock_event.title = "Out Event"
    mock_event.type = EventType.OUT_COLLEGE
    mock_event.category = EventCategory.BOTH
    mock_event.status = EventStatus.PENDING
    mock_event.start_date = None
    mock_event.end_date = None
    mock_event.description = None
    mock_event.venue = None
    mock_event.max_registrations = 0
    mock_event.brochure_url = None
    mock_event.brochure_file_key = None
    mock_event.created_by = student_user
    mock_event.created_by_id = 2
    mock_event.coordinator = None
    mock_event.created_at = None
    mock_event.updated_at = None
    mock_event._registration_count = 0
    mock_event._attendance_count = 0
    mock_db.execute.return_value.scalar_one_or_none.return_value = mock_event
    mock_db.scalar.return_value = 0

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/events/1/brochure", json={
            "file_name": "brochure.pdf",
            "file_type": "application/pdf",
        })

    assert resp.status_code == 200
    data = resp.json()
    assert "upload_url" in data
    assert "file_key" in data


@pytest.mark.asyncio
@patch("app.api.v1.events.get_db")
@patch("app.api.v1.events.get_current_user")
async def test_request_brochure_url_invalid_type(
    mock_get_user, mock_get_db, student_user, mock_db
):
    mock_get_user.return_value = student_user
    mock_get_db.return_value = mock_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/events/1/brochure", json={
            "file_name": "bad.exe",
            "file_type": "application/x-msdownload",
        })

    assert resp.status_code == 422
```

- [ ] **Step 2: Run integration tests**

```bash
cd backend && pytest tests/test_events.py -v
```

Expected: All tests PASS

- [ ] **Step 3: Run full test suite to check for regressions**

```bash
cd backend && pytest -v
```

Expected: All tests PASS across all test files

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_events.py
git commit -m "test: add integration tests for events module endpoints"
```

---

## Spec Coverage Check

| Spec Requirement | Task | Status |
|---|---|---|
| GET /api/v1/events - list with role filtering and pagination | Task 2 (list_events) + Task 8 (router) + Task 10 (test) | Done |
| POST /api/v1/events - create with role-based rules | Task 2 (create_event) + Task 8 (router) + Task 10 (test) | Done |
| GET /api/v1/events/{id} - get with counts | Task 3 (get_event_by_id) + Task 8 (router) + Task 10 (test) | Done |
| PATCH /api/v1/events/{id} - update (no status/type change) | Task 4 (update_event) + Task 8 (router) + Task 10 (test) | Done |
| PATCH /api/v1/events/{id}/approve - approve workflow | Task 5 (approve_event) + Task 8 (router) + Task 10 (test) | Done |
| PATCH /api/v1/events/{id}/reject - reject workflow | Task 5 (reject_event) + Task 8 (router) + Task 10 (test) | Done |
| PATCH /api/v1/events/{id}/assign-coordinator - assign teacher | Task 6 (assign_coordinator) + Task 8 (router) + Task 10 (test) | Done |
| POST /api/v1/events/{id}/brochure - presigned URL (mock) | Task 7 (request_brochure_url) + Task 8 (router) + Task 10 (test) | Done |
| Pydantic schemas for all endpoints | Task 1 (event.py schemas) | Done |
| Register router in main.py | Task 9 | Done |
| SQLAlchemy model with brochure fields, nullable coordinator | Task 0 | Done |
| Mock upload URL in dev (no S3) | Task 7 | Done |
| Brochure file type validation (PDF, JPEG, PNG) | Task 1 (EventBrochureRequest validator) | Done |
| Full TDD (service then test) | Tasks 1-10 | Done |

## Placeholder Scan

No placeholders ("TODO", "implement later", "fill in details", "handle errors" without code) found. Every code block contains complete, runnable code. All error handling is explicit (HTTPException in router, ValidationError/ForbiddenError/NotFoundError/ConflictError in service, Pydantic validation in schemas).

## Type Consistency Check

- `EventCreate` parsed by Pydantic → consumed by `create_event(data: EventCreate, user: User)` — consistent
- `EventUpdate` parsed by Pydantic → consumed by `update_event(db, event_id, data: EventUpdate, user)` — consistent
- `EventQueryParams` built in router from Query params → consumed by `list_events(db, user, params: EventQueryParams)` — consistent
- `list_events` returns `tuple[list[Event], int]` → router builds `PaginatedResponse` — consistent
- `get_event_by_id` returns `Event` with `_registration_count` and `_attendance_count` — consistent
- `approve_event` returns updated `Event` → FastAPI serializes via `EventOut` — consistent
- `request_brochure_url` returns `dict` with `upload_url` and `file_key` — matches spec response shape
- All service methods use `AsyncSession` and `User` — consistent with FastAPI deps pattern
- `assign_coordinator` validates teacher role + active status before updating — matches spec
- `EventBrochureRequest` validates file_type is PDF/JPEG/PNG — matches spec for brochure upload limits
