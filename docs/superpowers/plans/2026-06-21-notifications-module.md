# In-App Notification System — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an in-app notification system — when registrations are accepted/rejected, events are approved/rejected, or teachers are approved/rejected, the affected user gets a DB notification viewable via API.

**Architecture:** New `Notification` model + `NotificationService` + `notifications` router. Existing services (Registration, Event, User) call `NotificationService.create_notification()` inside their methods (same DB transaction). No email delivery.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 async, asyncpg, PostgreSQL, Pydantic v2

---

## File Map

| Action | File | Responsibility |
|---|---|---|
| CREATE | `app/models/notification.py` | `Notification` model + `NotificationType` enum |
| MODIFY | `app/models/__init__.py` | Export new model + enum |
| CREATE | `app/schemas/notification.py` | Pydantic schemas for notification responses |
| MODIFY | `app/schemas/__init__.py` | Export notification schemas |
| CREATE | `app/services/notification.py` | `NotificationService` (CRUD + helpers) |
| CREATE | `app/api/v1/notifications.py` | 4 endpoints (list, unread-count, mark-read, read-all) |
| MODIFY | `app/main.py` | Register notifications router + OpenAPI tag |
| MODIFY | `app/services/registration.py` | Add notification call in accept/reject |
| MODIFY | `app/services/event.py` | Add notification call in approve/reject |
| MODIFY | `app/services/user.py` | Add notification call in approve/reject |
| CREATE | `alembic/versions/0002_notifications.py` | Migration for `notifications` table |
| CREATE | `tests/test_notifications.py` | All tests (schema, service, API, integration) |

---

### Task 1: Notification Model + Alembic Migration

**Files:**
- Create: `app/models/notification.py`
- Modify: `app/models/__init__.py`
- Create: `alembic/versions/0002_notifications.py`

- [ ] **Step 1: Create `app/models/notification.py`**

```python
import enum
import uuid
from typing import Optional
from datetime import datetime
from sqlalchemy import String, Text, Boolean, Enum as SAEnum, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base, TimestampMixin


class NotificationType(str, enum.Enum):
    REGISTRATION_ACCEPTED = "registration_accepted"
    REGISTRATION_REJECTED = "registration_rejected"
    EVENT_APPROVED = "event_approved"
    EVENT_REJECTED = "event_rejected"
    TEACHER_APPROVED = "teacher_approved"
    TEACHER_REJECTED = "teacher_rejected"


class Notification(TimestampMixin, Base):
    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    type: Mapped[NotificationType] = mapped_column(
        SAEnum(NotificationType), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    related_entity_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    related_entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
```

- [ ] **Step 2: Update `app/models/__init__.py`**

Edit to add import and `__all__` entry:

```python
from app.models.notification import Notification, NotificationType

# In __all__ add:
    "Notification", "NotificationType",
```

- [ ] **Step 3: Create migration `alembic/versions/0002_notifications.py`**

Generating via alembic would require a live DB. Instead write the migration manually:

```python
"""add_notifications_table

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-21 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column(
            "type",
            sa.Enum(
                "registration_accepted", "registration_rejected",
                "event_approved", "event_rejected",
                "teacher_approved", "teacher_rejected",
                name="notificationtype",
            ),
            nullable=False,
        ),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("related_entity_type", sa.String(50), nullable=True),
        sa.Column("related_entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_read", sa.Boolean, nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_table("notifications")
    op.execute("DROP TYPE IF EXISTS notificationtype")
```

- [ ] **Step 4: Run tests to verify model imports without error**

Run: `python -c "from app.models import Notification, NotificationType; print('OK')"`
Expected: Prints "OK"

- [ ] **Step 5: Commit**

```bash
git add app/models/notification.py app/models/__init__.py alembic/versions/0002_notifications.py
git commit -m "feat(notifications): add Notification model + NotificationType enum + migration"
```

---

### Task 2: Notification Schemas

**Files:**
- Create: `app/schemas/notification.py`
- Modify: `app/schemas/__init__.py`

- [ ] **Step 1: Create `app/schemas/notification.py`**

```python
import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class NotificationOut(BaseModel):
    id: str
    type: str
    title: str
    message: str
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[str] = None
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UnreadCountResponse(BaseModel):
    count: int


class MarkReadAllResponse(BaseModel):
    count: int
```

- [ ] **Step 2: Update `app/schemas/__init__.py`**

```python
from app.schemas.notification import NotificationOut, UnreadCountResponse, MarkReadAllResponse

# In __all__ add:
    "NotificationOut", "UnreadCountResponse", "MarkReadAllResponse",
```

- [ ] **Step 3: Commit**

```bash
git add app/schemas/notification.py app/schemas/__init__.py
git commit -m "feat(notifications): add Pydantic schemas"
```

---

### Task 3: Notification Service + Tests

**Files:**
- Create: `app/services/notification.py`
- Create: `tests/test_notifications.py` (service tests section)

- [ ] **Step 1: Write the service tests (failing)**

Append to `tests/test_notifications.py` — these test the NotificationService directly with mocked DB:

```python
import uuid
from unittest.mock import AsyncMock, MagicMock
import pytest
from sqlalchemy import select, func

USER_ID = uuid.uuid4()
OTHER_USER_ID = uuid.uuid4()
NOTIF_ID = uuid.uuid4()

# ── Helper to create a mock Notification ──

def _make_notif(id=NOTIF_ID, user_id=USER_ID, type="registration_accepted",
                title="Test", message="Test msg", is_read=False):
    n = MagicMock()
    n.id = id
    n.user_id = user_id
    n.type = type
    n.title = title
    n.message = message
    n.is_read = is_read
    n.created_at = MagicMock()
    n.related_entity_type = None
    n.related_entity_id = None
    return n


class TestNotificationService:

    @pytest.mark.asyncio
    async def test_create_notification(self):
        from app.services.notification import NotificationService

        db = AsyncMock()

        notif = await NotificationService.create_notification(
            db, user_id=USER_ID, type="registration_accepted",
            title="Accepted", message="You are accepted",
            entity_type="registration", entity_id=uuid.uuid4(),
        )

        db.add.assert_called_once()
        db.commit.assert_called_once()
        assert notif.user_id == USER_ID
        assert notif.type == "registration_accepted"

    @pytest.mark.asyncio
    async def test_get_user_notifications_paginated(self):
        from app.services.notification import NotificationService

        db = AsyncMock()
        mock_notif = _make_notif()
        db.execute.return_value = MagicMock(
            scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[mock_notif])))
        )
        # Mock the count query as well
        db.scalar.return_value = 1

        notifs, total = await NotificationService.get_user_notifications(
            db, user_id=USER_ID, page=1, limit=20,
        )

        assert len(notifs) == 1
        assert total == 1
        assert db.execute.call_count >= 1

    @pytest.mark.asyncio
    async def test_get_user_notifications_unread_only(self):
        from app.services.notification import NotificationService

        db = AsyncMock()
        notifs_result = MagicMock(
            scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[_make_notif()])))
        )
        db.scalar.return_value = 1
        db.execute.return_value = notifs_result

        notifs, total = await NotificationService.get_user_notifications(
            db, user_id=USER_ID, page=1, limit=20, unread_only=True,
        )

        assert len(notifs) == 1

    @pytest.mark.asyncio
    async def test_get_user_notifications_empty_other_user(self):
        from app.services.notification import NotificationService

        db = AsyncMock()
        db.scalar.return_value = 0
        db.execute.return_value = MagicMock(
            scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        )

        notifs, total = await NotificationService.get_user_notifications(
            db, user_id=OTHER_USER_ID, page=1, limit=20,
        )

        assert notifs == []
        assert total == 0

    @pytest.mark.asyncio
    async def test_mark_as_read_success(self):
        from app.services.notification import NotificationService

        db = AsyncMock()
        mock_notif = _make_notif(is_read=False)
        mock_notif.id = NOTIF_ID
        mock_notif.user_id = USER_ID
        db.get.return_value = mock_notif

        result = await NotificationService.mark_as_read(db, NOTIF_ID, USER_ID)

        assert result.is_read is True
        db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_mark_as_read_not_found(self):
        from app.services.notification import NotificationService
        from app.core.exceptions import NotFoundException

        db = AsyncMock()
        db.get.return_value = None

        with pytest.raises(NotFoundException):
            await NotificationService.mark_as_read(db, NOTIF_ID, USER_ID)

    @pytest.mark.asyncio
    async def test_mark_as_read_wrong_user(self):
        from app.services.notification import NotificationService
        from app.core.exceptions import ForbiddenException

        db = AsyncMock()
        mock_notif = _make_notif(is_read=False)
        mock_notif.user_id = OTHER_USER_ID
        db.get.return_value = mock_notif

        with pytest.raises(ForbiddenException):
            await NotificationService.mark_as_read(db, NOTIF_ID, USER_ID)

    @pytest.mark.asyncio
    async def test_mark_all_as_read(self):
        from app.services.notification import NotificationService

        db = AsyncMock()
        db.execute.return_value = MagicMock(
            scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[
                _make_notif(id=uuid.uuid4(), is_read=False),
                _make_notif(id=uuid.uuid4(), is_read=False),
            ])))
        )

        count = await NotificationService.mark_all_as_read(db, USER_ID)

        assert count == 2
        db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_mark_all_as_read_other_user_unaffected(self):
        from app.services.notification import NotificationService

        db = AsyncMock()
        # Only return notifications for OTHER_USER_ID
        db.execute.return_value = MagicMock(
            scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        )

        count = await NotificationService.mark_all_as_read(db, OTHER_USER_ID)

        assert count == 0

    @pytest.mark.asyncio
    async def test_get_unread_count(self):
        from app.services.notification import NotificationService

        db = AsyncMock()
        db.scalar.return_value = 3

        count = await NotificationService.get_unread_count(db, USER_ID)

        assert count == 3

    @pytest.mark.asyncio
    async def test_get_unread_count_zero(self):
        from app.services.notification import NotificationService

        db = AsyncMock()
        db.scalar.return_value = 0

        count = await NotificationService.get_unread_count(db, USER_ID)

        assert count == 0
```

- [ ] **Step 2: Run the test file to verify failures**

Run: `pytest tests/test_notifications.py::TestNotificationService -v`
Expected: All fail with `ModuleNotFoundError: No module named 'app.services.notification'`

- [ ] **Step 3: Create `app/services/notification.py`**

```python
import uuid
from typing import Optional
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.notification import Notification, NotificationType
from app.core.exceptions import NotFoundException, ForbiddenException


NOTIFICATION_TEMPLATES = {
    NotificationType.REGISTRATION_ACCEPTED: (
        "Registration Accepted",
        lambda ctx: f'Your registration for "{ctx["event_title"]}" as {ctx["role"]} has been accepted.',
    ),
    NotificationType.REGISTRATION_REJECTED: (
        "Registration Rejected",
        lambda ctx: f'Your registration for "{ctx["event_title"]}" as {ctx["role"]} has been rejected.',
    ),
    NotificationType.EVENT_APPROVED: (
        "Event Approved",
        lambda ctx: f'Your event "{ctx["event_title"]}" has been approved.',
    ),
    NotificationType.EVENT_REJECTED: (
        "Event Rejected",
        lambda ctx: f'Your event "{ctx["event_title"]}" has been rejected.',
    ),
    NotificationType.TEACHER_APPROVED: (
        "Account Approved",
        lambda _ctx: "Your teacher account has been approved. You can now log in and create events.",
    ),
    NotificationType.TEACHER_REJECTED: (
        "Account Rejected",
        lambda _ctx: "Your teacher account request has been rejected.",
    ),
}


def _render_notification(
    notif_type: NotificationType,
    context: dict | None = None,
) -> tuple[str, str]:
    context = context or {}
    title, msg_fn = NOTIFICATION_TEMPLATES[notif_type]
    return title, msg_fn(context)


class NotificationService:

    @staticmethod
    async def create_notification(
        db: AsyncSession,
        user_id: uuid.UUID,
        type: NotificationType,
        title: str,
        message: str,
        entity_type: Optional[str] = None,
        entity_id: Optional[uuid.UUID] = None,
    ) -> Notification:
        notif = Notification(
            user_id=user_id,
            type=type,
            title=title,
            message=message,
            related_entity_type=entity_type,
            related_entity_id=entity_id,
        )
        db.add(notif)
        await db.commit()
        await db.refresh(notif)
        return notif

    @staticmethod
    async def get_user_notifications(
        db: AsyncSession,
        user_id: uuid.UUID,
        page: int = 1,
        limit: int = 20,
        unread_only: bool = False,
    ) -> tuple[list[Notification], int]:
        stmt = select(Notification).where(Notification.user_id == user_id)
        count_stmt = select(func.count()).select_from(Notification).where(
            Notification.user_id == user_id
        )

        if unread_only:
            stmt = stmt.where(Notification.is_read == False)
            count_stmt = count_stmt.where(Notification.is_read == False)

        stmt = (
            stmt
            .order_by(Notification.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )

        total = await db.scalar(count_stmt) or 0
        result = await db.execute(stmt)
        notifs = list(result.scalars().all())
        return notifs, total

    @staticmethod
    async def mark_as_read(
        db: AsyncSession,
        notification_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Notification:
        notif = await db.get(Notification, notification_id)
        if not notif:
            raise NotFoundException("Notification not found")
        if notif.user_id != user_id:
            raise ForbiddenException("You do not own this notification")
        notif.is_read = True
        await db.commit()
        await db.refresh(notif)
        return notif

    @staticmethod
    async def mark_all_as_read(
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> int:
        stmt = (
            select(Notification)
            .where(Notification.user_id == user_id, Notification.is_read == False)
        )
        result = await db.execute(stmt)
        notifs = list(result.scalars().all())
        count = len(notifs)
        for n in notifs:
            n.is_read = True
        if count:
            await db.commit()
        return count

    @staticmethod
    async def get_unread_count(
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> int:
        stmt = select(func.count()).select_from(Notification).where(
            Notification.user_id == user_id,
            Notification.is_read == False,
        )
        total = await db.scalar(stmt) or 0
        return total
```

- [ ] **Step 4: Run service tests to verify they pass**

Run: `pytest tests/test_notifications.py::TestNotificationService -v`
Expected: All pass

- [ ] **Step 5: Commit**

```bash
git add app/services/notification.py tests/test_notifications.py
git commit -m "feat(notifications): add NotificationService with tests"
```

---

### Task 4: Notification Router + API Tests

**Files:**
- Create: `app/api/v1/notifications.py`
- Modify: `tests/test_notifications.py` (append API tests section)

- [ ] **Step 1: Write API tests for the notifications router**

Append to `tests/test_notifications.py`:

```python
class TestNotificationAPI:
    UUID_STR = str(uuid.uuid4())

    @pytest.fixture(autouse=True)
    def _setup(self):
        self.student_user = {"sub": str(USER_ID), "role": "student"}
        self.other_user = {"sub": str(OTHER_USER_ID), "role": "student"}

    @pytest.mark.asyncio
    async def test_list_notifications(self):
        from fastapi import FastAPI
        from app.api.v1.notifications import router
        from app.api.deps import get_current_user

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_current_user] = lambda: self.student_user

        from app.services.notification import NotificationService

        mock_notif = MagicMock()
        mock_notif.id = NOTIF_ID
        mock_notif.user_id = USER_ID
        mock_notif.type = "registration_accepted"
        mock_notif.title = "Accepted"
        mock_notif.message = "You are accepted"
        mock_notif.is_read = False
        mock_notif.created_at = datetime(2026, 6, 21, 10, 0, 0)
        mock_notif.related_entity_type = None
        mock_notif.related_entity_id = None

        with patch.object(NotificationService, "get_user_notifications", new=AsyncMock(return_value=([mock_notif], 1))):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/notifications")

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert len(data["data"]) == 1
        assert data["data"][0]["title"] == "Accepted"

    @pytest.mark.asyncio
    async def test_list_notifications_unread_only(self):
        from fastapi import FastAPI
        from app.api.v1.notifications import router
        from app.api.deps import get_current_user

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_current_user] = lambda: self.student_user

        from app.services.notification import NotificationService

        with patch.object(NotificationService, "get_user_notifications", new=AsyncMock(return_value=([], 0))):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/notifications?unread_only=true")

        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_unread_count(self):
        from fastapi import FastAPI
        from app.api.v1.notifications import router
        from app.api.deps import get_current_user

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_current_user] = lambda: self.student_user

        from app.services.notification import NotificationService

        with patch.object(NotificationService, "get_unread_count", new=AsyncMock(return_value=3)):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/notifications/unread-count")

        assert resp.status_code == 200
        assert resp.json()["data"]["count"] == 3

    @pytest.mark.asyncio
    async def test_mark_as_read(self):
        from fastapi import FastAPI
        from app.api.v1.notifications import router
        from app.api.deps import get_current_user

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_current_user] = lambda: self.student_user

        from app.services.notification import NotificationService

        mock_notif = MagicMock()
        mock_notif.is_read = True

        with patch.object(NotificationService, "mark_as_read", new=AsyncMock(return_value=mock_notif)):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.patch(f"/api/v1/notifications/{NOTIF_ID}/read")

        assert resp.status_code == 200
        assert resp.json()["data"]["is_read"] is True

    @pytest.mark.asyncio
    async def test_mark_as_read_not_found(self):
        from fastapi import FastAPI
        from app.api.v1.notifications import router
        from app.api.deps import get_current_user
        from app.core.exceptions import NotFoundException

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_current_user] = lambda: self.student_user

        from app.services.notification import NotificationService

        with patch.object(NotificationService, "mark_as_read", new=AsyncMock(side_effect=NotFoundException("Not found"))):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.patch(f"/api/v1/notifications/{NOTIF_ID}/read")

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_mark_all_as_read(self):
        from fastapi import FastAPI
        from app.api.v1.notifications import router
        from app.api.deps import get_current_user

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_current_user] = lambda: self.student_user

        from app.services.notification import NotificationService

        with patch.object(NotificationService, "mark_all_as_read", new=AsyncMock(return_value=2)):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.patch("/api/v1/notifications/read-all")

        assert resp.status_code == 200
        assert resp.json()["data"]["count"] == 2

    @pytest.mark.asyncio
    async def test_notifications_unauthorized(self):
        from fastapi import FastAPI
        from app.api.v1.notifications import router
        from app.api.deps import get_current_user

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_current_user] = lambda: None

        from app.core.exceptions import UnauthorizedException

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/notifications")

        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_mark_read_unauthorized(self):
        from fastapi import FastAPI
        from app.api.v1.notifications import router
        from app.api.deps import get_current_user

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_current_user] = lambda: None

        from app.core.exceptions import UnauthorizedException

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.patch(f"/api/v1/notifications/{NOTIF_ID}/read")

        assert resp.status_code == 401
```

- [ ] **Step 2: Run API tests — they should fail**

Run: `pytest tests/test_notifications.py::TestNotificationAPI -v`
Expected: Fail with `ModuleNotFoundError`

- [ ] **Step 3: Create `app/api/v1/notifications.py`**

```python
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user
from app.core.database import get_db
from app.schemas.common import SuccessResponse, PaginatedResponse, PaginatedMeta
from app.schemas.notification import NotificationOut, UnreadCountResponse, MarkReadAllResponse
from app.services.notification import NotificationService

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


@router.get("")
async def list_notifications(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    unread_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = uuid.UUID(current_user["sub"])
    notifs, total = await NotificationService.get_user_notifications(
        db, user_id, page=page, limit=limit, unread_only=unread_only,
    )
    total_pages = max(1, (total + limit - 1) // limit) if total else 0
    return PaginatedResponse(
        success=True,
        data=[_notif_to_out(n) for n in notifs],
        meta=PaginatedMeta(page=page, limit=limit, total=total, total_pages=total_pages),
    )


@router.get("/unread-count")
async def unread_count(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = uuid.UUID(current_user["sub"])
    count = await NotificationService.get_unread_count(db, user_id)
    return SuccessResponse(data=UnreadCountResponse(count=count))


@router.patch("/{id}/read")
async def mark_as_read(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = uuid.UUID(current_user["sub"])
    notif = await NotificationService.mark_as_read(db, id, user_id)
    return SuccessResponse(data=_notif_to_out(notif))


@router.patch("/read-all")
async def mark_all_as_read(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = uuid.UUID(current_user["sub"])
    count = await NotificationService.mark_all_as_read(db, user_id)
    return SuccessResponse(data=MarkReadAllResponse(count=count))


def _notif_to_out(n) -> dict:
    return NotificationOut(
        id=str(n.id),
        type=n.type.value if hasattr(n.type, "value") else n.type,
        title=n.title,
        message=n.message,
        related_entity_type=n.related_entity_type,
        related_entity_id=str(n.related_entity_id) if n.related_entity_id else None,
        is_read=n.is_read,
        created_at=n.created_at,
    )
```

- [ ] **Step 4: Run API tests — they should pass**

Run: `pytest tests/test_notifications.py::TestNotificationAPI -v`
Expected: All pass

- [ ] **Step 5: Commit**

```bash
git add app/api/v1/notifications.py tests/test_notifications.py
git commit -m "feat(notifications): add notifications router + API tests"
```

---

### Task 5: Register Router in main.py + OpenAPI Tag

**Files:**
- Modify: `app/main.py`

- [ ] **Step 1: Register the notifications router and tag in `app/main.py`**

Add import:
```python
from app.api.v1.notifications import router as notifications_router
```

Add to `app.include_router(...)` section:
```python
app.include_router(notifications_router)
```

Add to `openapi_tags`:
```python
{"name": "notifications", "description": "In-app notifications"},
```

- [ ] **Step 2: Run full suite to verify nothing broken**

Run: `pytest --tb=line`
Expected: 193+ tests pass (exact count depends on previous state)

- [ ] **Step 3: Commit**

```bash
git add app/main.py
git commit -m "feat(notifications): register notifications router + OpenAPI tag"
```

---

### Task 6: Integration — Registration Accept/Reject Notifications

**Files:**
- Modify: `app/services/registration.py` (add notification calls in accept_registration and reject_registration)
- Modify: `tests/test_notifications.py` (append integration tests)

- [ ] **Step 1: Write integration tests for registration notifications**

Append to `tests/test_notifications.py`:

```python
class TestRegistrationNotificationIntegration:

    @pytest.mark.asyncio
    async def test_accept_registration_creates_notification(self):
        from app.services.registration import RegistrationService
        from app.services.notification import NotificationService

        db = AsyncMock()
        mock_reg = MagicMock()
        mock_reg.status = "pending"
        mock_reg.student_id = USER_ID
        mock_reg.event_id = uuid.uuid4()

        mock_event = MagicMock()
        mock_event.title = "Tech Fest"
        mock_event.coordinator_id = TEACHER_ID

        # accept_registration calls db.get twice: first for reg, then for event
        db.get = AsyncMock(side_effect=[mock_reg, mock_event])

        with patch.object(NotificationService, "create_notification", new=AsyncMock()) as mock_create:
            await RegistrationService.accept_registration(
                db, NOTIF_ID,
                {"sub": str(TEACHER_ID), "role": "teacher"},
            )

        mock_create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_reject_registration_creates_notification(self):
        from app.services.registration import RegistrationService
        from app.services.notification import NotificationService

        db = AsyncMock()
        mock_reg = MagicMock()
        mock_reg.status = "pending"
        mock_reg.student_id = USER_ID
        mock_reg.event_id = uuid.uuid4()

        mock_event = MagicMock()
        mock_event.title = "Tech Fest"
        mock_event.coordinator_id = TEACHER_ID

        db.get = AsyncMock(side_effect=[mock_reg, mock_event])

        with patch.object(NotificationService, "create_notification", new=AsyncMock()) as mock_create:
            await RegistrationService.reject_registration(
                db, NOTIF_ID,
                {"sub": str(TEACHER_ID), "role": "teacher"},
            )

        mock_create.assert_awaited_once()
```

- [ ] **Step 2: Run integration tests (failing)**

Run: `pytest tests/test_notifications.py::TestRegistrationNotificationIntegration -v`
Expected: Fails because registration.py doesn't call NotificationService yet

- [ ] **Step 3: Add notification calls to `RegistrationService.accept_registration` and `reject_registration`**

In `accept_registration`, add imports at top:
```python
from app.services.notification import NotificationService, NotificationType, _render_notification
```

Inside `accept_registration`, after `reg.status = RegistrationStatus.ACCEPTED` and before `await db.commit()`:
```python
        reg.status = RegistrationStatus.ACCEPTED
        title, message = _render_notification(
            NotificationType.REGISTRATION_ACCEPTED,
            {"event_title": event.title, "role": reg.role_type.value if hasattr(reg.role_type, "value") else reg.role_type},
        )
        await NotificationService.create_notification(
            db,
            user_id=reg.student_id,
            type=NotificationType.REGISTRATION_ACCEPTED,
            title=title,
            message=message,
            entity_type="registration",
            entity_id=reg.id,
        )
        await db.commit()
```

Inside `reject_registration`, after `reg.status = RegistrationStatus.REJECTED` and before `await db.commit()`:
```python
        reg.status = RegistrationStatus.REJECTED
        title, message = _render_notification(
            NotificationType.REGISTRATION_REJECTED,
            {"event_title": event.title, "role": reg.role_type.value if hasattr(reg.role_type, "value") else reg.role_type},
        )
        await NotificationService.create_notification(
            db,
            user_id=reg.student_id,
            type=NotificationType.REGISTRATION_REJECTED,
            title=title,
            message=message,
            entity_type="registration",
            entity_id=reg.id,
        )
        await db.commit()
```

- [ ] **Step 4: Run integration tests (should pass)**

Run: `pytest tests/test_notifications.py::TestRegistrationNotificationIntegration -v`
Expected: All pass

- [ ] **Step 5: Run full existing registration tests to verify no regressions**

Run: `pytest tests/test_registrations.py -v`
Expected: All pass

- [ ] **Step 6: Commit**

```bash
git add app/services/registration.py tests/test_notifications.py
git commit -m "feat(notifications): integrate registration accept/reject notifications"
```

---

### Task 7: Integration — Event Approve/Reject Notifications

**Files:**
- Modify: `app/services/event.py` (add notification calls in approve_event and reject_event)
- Modify: `tests/test_notifications.py` (append integration tests)

- [ ] **Step 1: Write integration tests for event notifications**

Append to `tests/test_notifications.py`:

```python
class TestEventNotificationIntegration:

    @pytest.mark.asyncio
    async def test_approve_event_creates_notification(self):
        from app.services.event import EventService
        from app.services.notification import NotificationService

        db = AsyncMock()
        mock_event = MagicMock()
        mock_event.status = "pending"
        mock_event.created_by = USER_ID
        mock_event.coordinator_id = TEACHER_ID
        mock_event.title = "Tech Fest"
        mock_event.event_type = "out_college"

        db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=mock_event))

        with patch.object(NotificationService, "create_notification", new=AsyncMock()) as mock_create:
            await EventService.approve_event(
                db, str(uuid.uuid4()), None,
                {"sub": str(TEACHER_ID), "role": "teacher"},
            )

        mock_create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_reject_event_creates_notification(self):
        from app.services.event import EventService
        from app.services.notification import NotificationService

        db = AsyncMock()
        mock_event = MagicMock()
        mock_event.status = "pending"
        mock_event.created_by = USER_ID
        mock_event.coordinator_id = TEACHER_ID
        mock_event.title = "Tech Fest"
        mock_event.event_type = "out_college"

        db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=mock_event))

        with patch.object(NotificationService, "create_notification", new=AsyncMock()) as mock_create:
            await EventService.reject_event(
                db, str(uuid.uuid4()), "Not suitable",
                {"sub": str(TEACHER_ID), "role": "teacher"},
            )

        mock_create.assert_awaited_once()
```

- [ ] **Step 2: Run integration tests (failing)**

Run: `pytest tests/test_notifications.py::TestEventNotificationIntegration -v`
Expected: Fails because event.py doesn't call NotificationService yet

- [ ] **Step 3: Add notification calls to `EventService.approve_event` and `reject_event`**

In `app/services/event.py`, add import at top:
```python
from app.services.notification import NotificationService, NotificationType, _render_notification
```

Inside `approve_event`, after `event.status = EventStatus.APPROVED` and before `await db.commit()`:
```python
        event.status = EventStatus.APPROVED
        title, message = _render_notification(
            NotificationType.EVENT_APPROVED,
            {"event_title": event.title},
        )
        await NotificationService.create_notification(
            db,
            user_id=event.created_by,
            type=NotificationType.EVENT_APPROVED,
            title=title,
            message=message,
            entity_type="event",
            entity_id=event.id,
        )
        await db.commit()
```

Inside `reject_event`, after `event.status = EventStatus.REJECTED` and before `await db.commit()`:
```python
        event.status = EventStatus.REJECTED
        title, message = _render_notification(
            NotificationType.EVENT_REJECTED,
            {"event_title": event.title},
        )
        await NotificationService.create_notification(
            db,
            user_id=event.created_by,
            type=NotificationType.EVENT_REJECTED,
            title=title,
            message=message,
            entity_type="event",
            entity_id=event.id,
        )
        await db.commit()
```

- [ ] **Step 4: Run integration tests (should pass)**

Run: `pytest tests/test_notifications.py::TestEventNotificationIntegration -v`
Expected: All pass

- [ ] **Step 5: Run full existing event tests to verify no regressions**

Run: `pytest tests/test_events.py -v`
Expected: All pass

- [ ] **Step 6: Commit**

```bash
git add app/services/event.py tests/test_notifications.py
git commit -m "feat(notifications): integrate event approve/reject notifications"
```

---

### Task 8: Integration — Teacher Approve/Reject Notifications

**Files:**
- Modify: `app/services/user.py` (add notification calls in approve_teacher and reject_teacher)
- Modify: `tests/test_notifications.py` (append integration tests)

- [ ] **Step 1: Write integration tests for teacher notifications**

Append to `tests/test_notifications.py`:

```python
class TestTeacherNotificationIntegration:

    @pytest.mark.asyncio
    async def test_approve_teacher_creates_notification(self):
        from app.services.user import approve_teacher
        from app.services.notification import NotificationService

        db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = USER_ID
        mock_user.role = "teacher"
        mock_user.status = "pending"
        mock_user.name = "John"
        mock_user.email = "john@college.edu"
        mock_user.created_at = MagicMock()
        mock_user.updated_at = MagicMock()

        db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=mock_user))

        with patch.object(NotificationService, "create_notification", new=AsyncMock()) as mock_create:
            await approve_teacher(db, str(USER_ID))

        mock_create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_reject_teacher_creates_notification(self):
        from app.services.user import reject_teacher
        from app.services.notification import NotificationService

        db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = USER_ID
        mock_user.role = "teacher"
        mock_user.status = "pending"
        mock_user.name = "John"
        mock_user.email = "john@college.edu"
        mock_user.created_at = MagicMock()
        mock_user.updated_at = MagicMock()

        db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=mock_user))

        with patch.object(NotificationService, "create_notification", new=AsyncMock()) as mock_create:
            await reject_teacher(db, str(USER_ID))

        mock_create.assert_awaited_once()
```

- [ ] **Step 2: Run integration tests (failing)**

Run: `pytest tests/test_notifications.py::TestTeacherNotificationIntegration -v`
Expected: Fails because user.py doesn't call NotificationService yet

- [ ] **Step 3: Add notification calls to `approve_teacher` and `reject_teacher` in `app/services/user.py`**

Add import near top:
```python
from app.services.notification import NotificationService, NotificationType, _render_notification
```

Inside `approve_teacher`, after `user.status = "active"` and before `await db.commit()`:
```python
    user.status = "active"
    title, message = _render_notification(NotificationType.TEACHER_APPROVED)
    await NotificationService.create_notification(
        db,
        user_id=user.id,
        type=NotificationType.TEACHER_APPROVED,
        title=title,
        message=message,
        entity_type="user",
        entity_id=user.id,
    )
    await db.commit()
```

Inside `reject_teacher`, after `user.status = "rejected"` and before `await db.commit()`:
```python
    user.status = "rejected"
    title, message = _render_notification(NotificationType.TEACHER_REJECTED)
    await NotificationService.create_notification(
        db,
        user_id=user.id,
        type=NotificationType.TEACHER_REJECTED,
        title=title,
        message=message,
        entity_type="user",
        entity_id=user.id,
    )
    await db.commit()
```

- [ ] **Step 4: Run integration tests (should pass)**

Run: `pytest tests/test_notifications.py::TestTeacherNotificationIntegration -v`
Expected: All pass

- [ ] **Step 5: Run full existing user tests to verify no regressions**

Run: `pytest tests/test_users.py -v`
Expected: All pass

- [ ] **Step 6: Commit**

```bash
git add app/services/user.py tests/test_notifications.py
git commit -m "feat(notifications): integrate teacher approve/reject notifications"
```

---

### Task 9: Full Verification

- [ ] **Step 1: Run entire test suite**

Run: `pytest --tb=line`
Expected: All tests pass (exact count depends on tests added + existing 193)

- [ ] **Step 2: Final commit if any changes were made during verification**

```bash
git add -A
git commit -m "chore: final touches after notification integration verification"
```
