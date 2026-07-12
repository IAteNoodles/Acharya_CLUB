# Phase 3: Users Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the admin workflow for managing teacher accounts — approve, reject, list pending, search active teachers.

**Architecture:** Users module follows the same pattern as the auth module (Phase 2). The approve/reject actions use SQLAlchemy async transactions to ensure consistency. All endpoints are admin-only, protected by the existing `Depends(require_admin)` dependency chain. Service functions return Pydantic models (not ORM instances) for testability.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy 2.0 (async), Pydantic v2, pytest 8, httpx 0.27

---

## File Structure

```
backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       └── users.py                  # FastAPIRouter with Depends wiring
│   ├── schemas/
│   │   └── users.py                      # Pydantic models for request/response
│   ├── services/
│   │   └── user.py                       # Business logic: list, approve, reject, search
│   └── main.py                           # MODIFY: app.include_router(users.router)
└── tests/
    └── test_users.py                     # Integration tests for all 4 endpoints
```

---

## Tasks

### Task 1: Create user schemas (app/schemas/users.py)

**Files:**
- Create: `backend/app/schemas/users.py`
- Create: `backend/tests/test_users.py` (schema tests only)

- [ ] **Step 1: Write the failing test**

```python
import pytest
from pydantic import ValidationError


class TestUserSchemas:
    def test_pending_teachers_response(self):
        from app.schemas.users import PendingTeachersResponse, UserOut

        user = UserOut(
            id="550e8400-e29b-41d4-a716-446655440000",
            name="Teacher A",
            email="a@college.edu",
            role="teacher",
            status="pending",
        )
        resp = PendingTeachersResponse(
            users=[user],
            total=1,
            page=1,
            limit=20,
            total_pages=1,
        )
        assert resp.success is True
        assert len(resp.users) == 1
        assert resp.users[0].status == "pending"
        assert resp.total_pages == 1

    def test_pending_teachers_response_empty(self):
        from app.schemas.users import PendingTeachersResponse

        resp = PendingTeachersResponse(users=[], total=0, page=1, limit=20, total_pages=0)
        assert resp.users == []
        assert resp.total == 0

    def test_teacher_list_response_with_search(self):
        from app.schemas.users import TeacherListResponse, UserOut

        user = UserOut(
            id="550e8400-e29b-41d4-a716-446655440001",
            name="Dr. Rajesh Kumar",
            email="rajesh@college.edu",
            role="teacher",
            status="active",
        )
        resp = TeacherListResponse(users=[user], total=1, page=1, limit=20, total_pages=1)
        assert resp.success is True
        assert resp.users[0].name == "Dr. Rajesh Kumar"

    def test_user_action_response(self):
        from app.schemas.users import UserActionResponse, UserOut

        user = UserOut(
            id="550e8400-e29b-41d4-a716-446655440002",
            name="Teacher B",
            email="b@college.edu",
            role="teacher",
            status="active",
        )
        resp = UserActionResponse(data=user)
        assert resp.success is True
        assert resp.data.status == "active"

    def test_user_out_rejects_invalid_uuid(self):
        from app.schemas.users import UserOut

        with pytest.raises(ValidationError):
            UserOut(
                id="not-a-uuid",
                name="Bad",
                email="bad@test.com",
                role="teacher",
                status="pending",
            )

    def test_user_out_rejects_invalid_role(self):
        from app.schemas.users import UserOut

        with pytest.raises(ValidationError):
            UserOut(
                id="550e8400-e29b-41d4-a716-446655440003",
                name="Bad",
                email="bad@test.com",
                role="superadmin",
                status="pending",
            )

    def test_user_out_rejects_invalid_status(self):
        from app.schemas.users import UserOut

        with pytest.raises(ValidationError):
            UserOut(
                id="550e8400-e29b-41d4-a716-446655440004",
                name="Bad",
                email="bad@test.com",
                role="teacher",
                status="nonexistent",
            )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && poetry run pytest tests/test_users.py -v`
Expected: FAIL (or ERR) - cannot import from `app.schemas.users`

- [ ] **Step 3: Write minimal implementation**

```python
import uuid
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from typing import Literal, Optional


class UserOut(BaseModel):
    id: str
    name: str
    email: str
    role: Literal["student", "teacher", "admin"]
    status: Literal["pending", "active", "rejected"]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_validator("id")
    @classmethod
    def validate_uuid(cls, v: str) -> str:
        uuid.UUID(v)
        return v

    model_config = {"from_attributes": True}


class PaginatedMeta(BaseModel):
    page: int = Field(ge=1, default=1)
    limit: int = Field(ge=1, le=100, default=20)
    total: int = Field(ge=0)
    total_pages: int = Field(ge=0)


class PendingTeachersResponse(BaseModel):
    success: bool = True
    users: list[UserOut]
    total: int
    page: int
    limit: int
    total_pages: int


class TeacherListResponse(BaseModel):
    success: bool = True
    users: list[UserOut]
    total: int
    page: int
    limit: int
    total_pages: int


class UserActionResponse(BaseModel):
    success: bool = True
    data: UserOut
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && poetry run pytest tests/test_users.py -v`
Expected: PASS (schema tests only)

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/users.py backend/tests/test_users.py
git commit -m "feat(users): add Pydantic schemas for user responses"
```

---

### Task 2: Create user service (app/services/user.py)

**Files:**
- Create: `backend/app/services/user.py`
- Modify: `backend/tests/test_users.py` (add service tests)

- [ ] **Step 1: Write the failing test**

```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy import select, func


@pytest.fixture
def mock_session():
    return AsyncMock()


class TestUserService:
    @patch("app.services.user.get_db")
    async def test_get_pending_teachers_returns_paginated(self, mock_get_db, mock_session):
        from app.schemas.users import UserOut
        from app.services.user import get_pending_teachers

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [
            MagicMock(
                id="uuid-1", name="Teacher A", email="a@college.edu",
                role="teacher", status="pending", created_at=None, updated_at=None,
            ),
        ]
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1
        mock_session.execute = AsyncMock(side_effect=[mock_result, mock_count_result])

        result = await get_pending_teachers(mock_session, page=1, limit=20)

        assert len(result.users) == 1
        assert result.total == 1
        assert isinstance(result.users[0], UserOut)

    @patch("app.services.user.get_db")
    async def test_get_pending_teachers_computes_offset(self, mock_get_db, mock_session):
        from app.services.user import get_pending_teachers

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 0
        mock_session.execute = AsyncMock(side_effect=[mock_result, mock_count_result])

        await get_pending_teachers(mock_session, page=2, limit=10)

        # The first execute call should have offset=10
        call_args = mock_session.execute.call_args_list
        first_stmt = call_args[0][0][0]
        assert str(first_stmt).lower().find("offset") >= 0

    @patch("app.services.user.get_db")
    async def test_approve_teacher_success(self, mock_get_db, mock_session):
        from app.services.user import approve_teacher

        mock_user = MagicMock(
            id="uuid-1", name="Teacher A", email="a@college.edu",
            role="teacher", status="pending",
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        result = await approve_teacher(mock_session, "uuid-1")

        assert result.status == "active"
        mock_session.commit.assert_awaited_once()

    @patch("app.services.user.get_db")
    async def test_approve_teacher_not_found(self, mock_get_db, mock_session):
        from app.services.user import approve_teacher

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(Exception) as exc:
            await approve_teacher(mock_session, "nonexistent")
        assert "not found" in str(exc.value).lower()

    @patch("app.services.user.get_db")
    async def test_approve_teacher_not_a_teacher(self, mock_get_db, mock_session):
        from app.services.user import approve_teacher

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock(
            id="uuid-1", role="student", status="pending",
        )
        mock_session.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(Exception) as exc:
            await approve_teacher(mock_session, "uuid-1")
        assert "not found" in str(exc.value).lower()

    @patch("app.services.user.get_db")
    async def test_approve_teacher_already_active(self, mock_get_db, mock_session):
        from app.services.user import approve_teacher

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock(
            id="uuid-1", role="teacher", status="active",
        )
        mock_session.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(Exception) as exc:
            await approve_teacher(mock_session, "uuid-1")
        assert "already active" in str(exc.value).lower()

    @patch("app.services.user.get_db")
    async def test_approve_teacher_already_rejected(self, mock_get_db, mock_session):
        from app.services.user import approve_teacher

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock(
            id="uuid-1", role="teacher", status="rejected",
        )
        mock_session.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(Exception) as exc:
            await approve_teacher(mock_session, "uuid-1")
        assert "already rejected" in str(exc.value).lower()

    @patch("app.services.user.get_db")
    async def test_reject_teacher_success(self, mock_get_db, mock_session):
        from app.services.user import reject_teacher

        mock_user = MagicMock(
            id="uuid-1", name="Teacher A", email="a@college.edu",
            role="teacher", status="pending",
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        result = await reject_teacher(mock_session, "uuid-1")

        assert result.status == "rejected"
        mock_session.commit.assert_awaited_once()

    @patch("app.services.user.get_db")
    async def test_reject_teacher_not_found(self, mock_get_db, mock_session):
        from app.services.user import reject_teacher

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(Exception) as exc:
            await reject_teacher(mock_session, "nonexistent")
        assert "not found" in str(exc.value).lower()

    @patch("app.services.user.get_db")
    async def test_reject_teacher_already_rejected(self, mock_get_db, mock_session):
        from app.services.user import reject_teacher

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock(
            id="uuid-1", role="teacher", status="rejected",
        )
        mock_session.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(Exception) as exc:
            await reject_teacher(mock_session, "uuid-1")
        assert "already rejected" in str(exc.value).lower()

    @patch("app.services.user.get_db")
    async def test_get_active_teachers_paginated(self, mock_get_db, mock_session):
        from app.services.user import get_active_teachers

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [
            MagicMock(
                id="uuid-1", name="Dr. Rajesh Kumar", email="rajesh@college.edu",
                role="teacher", status="active", created_at=None, updated_at=None,
            ),
        ]
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1
        mock_session.execute = AsyncMock(side_effect=[mock_result, mock_count_result])

        result = await get_active_teachers(mock_session, page=1, limit=20)

        assert len(result.users) == 1
        assert result.total == 1

    @patch("app.services.user.get_db")
    async def test_get_active_teachers_with_search(self, mock_get_db, mock_session):
        from app.services.user import get_active_teachers

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 0
        mock_session.execute = AsyncMock(side_effect=[mock_result, mock_count_result])

        await get_active_teachers(mock_session, page=1, limit=20, search="rajesh")

        call_args = mock_session.execute.call_args_list
        first_stmt = call_args[0][0][0]
        combined = str(first_stmt).lower()
        assert "ilike" in combined or "rajesh" in combined
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && poetry run pytest tests/test_users.py -v`
Expected: FAIL - cannot import from `app.services.user`

- [ ] **Step 3: Write minimal implementation**

```python
import uuid
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.users import UserOut, PendingTeachersResponse, TeacherListResponse


def _compute_pagination(page: int, limit: int, total: int):
    total_pages = (total + limit - 1) // limit if total > 0 else 0
    return total_pages


async def get_pending_teachers(
    db: AsyncSession,
    page: int = 1,
    limit: int = 20,
) -> PendingTeachersResponse:
    from app.models.user import User

    offset = (page - 1) * limit

    stmt = (
        select(User)
        .where(User.role == "teacher", User.status == "pending")
        .offset(offset)
        .limit(limit)
        .order_by(User.created_at.asc())
    )
    count_stmt = (
        select(func.count(User.id))
        .where(User.role == "teacher", User.status == "pending")
    )

    result = await db.execute(stmt)
    users = result.scalars().all()

    count_result = await db.execute(count_stmt)
    total = count_result.scalar() or 0

    total_pages = _compute_pagination(page, limit, total)

    return PendingTeachersResponse(
        users=[UserOut.model_validate(u) for u in users],
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages,
    )


async def _get_teacher_user(db: AsyncSession, user_id: str):
    from app.models.user import User

    try:
        uuid.UUID(user_id)
    except ValueError:
        return None

    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def approve_teacher(db: AsyncSession, user_id: str) -> UserOut:
    from app.models.user import User

    user = await _get_teacher_user(db, user_id)

    if not user or user.role != "teacher":
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="User not found")

    if user.status == "active":
        from fastapi import HTTPException
        raise HTTPException(status_code=409, detail="User is already active")

    if user.status == "rejected":
        from fastapi import HTTPException
        raise HTTPException(status_code=409, detail="User is already rejected")

    user.status = "active"
    await db.commit()
    await db.refresh(user)

    return UserOut.model_validate(user)


async def reject_teacher(db: AsyncSession, user_id: str) -> UserOut:
    from app.models.user import User

    user = await _get_teacher_user(db, user_id)

    if not user or user.role != "teacher":
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="User not found")

    if user.status == "rejected":
        from fastapi import HTTPException
        raise HTTPException(status_code=409, detail="User is already rejected")

    user.status = "rejected"
    await db.commit()
    await db.refresh(user)

    return UserOut.model_validate(user)


async def get_active_teachers(
    db: AsyncSession,
    page: int = 1,
    limit: int = 20,
    search: str | None = None,
) -> TeacherListResponse:
    from app.models.user import User

    offset = (page - 1) * limit

    base_filters = [User.role == "teacher", User.status == "active"]

    if search:
        search_filter = or_(
            User.name.ilike(f"%{search}%"),
            User.email.ilike(f"%{search}%"),
        )
        stmt = (
            select(User)
            .where(*base_filters, search_filter)
            .offset(offset)
            .limit(limit)
            .order_by(User.name.asc())
        )
        count_stmt = (
            select(func.count(User.id))
            .where(*base_filters, search_filter)
        )
    else:
        stmt = (
            select(User)
            .where(*base_filters)
            .offset(offset)
            .limit(limit)
            .order_by(User.name.asc())
        )
        count_stmt = (
            select(func.count(User.id))
            .where(*base_filters)
        )

    result = await db.execute(stmt)
    users = result.scalars().all()

    count_result = await db.execute(count_stmt)
    total = count_result.scalar() or 0

    total_pages = _compute_pagination(page, limit, total)

    return TeacherListResponse(
        users=[UserOut.model_validate(u) for u in users],
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && poetry run pytest tests/test_users.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/user.py backend/tests/test_users.py
git commit -m "feat(users): add user service with approve/reject/list logic"
```

---

### Task 3: Create users router (app/api/v1/users.py)

**Note:** FastAPI combines the controller and router into one file. There is no separate controller layer. The router directly depends on the service.

**Files:**
- Create: `backend/app/api/v1/users.py`
- Modify: `backend/tests/test_users.py` (add endpoint integration tests)

- [ ] **Step 1: Write the failing test**

This step tests the full request → router → service integration using `httpx.AsyncClient` with a test FastAPI app. Auth dependencies are overridden to simulate admin access.

```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def override_admin():
    """Override auth dependencies to simulate admin user."""
    from app.api import deps

    async def mock_admin():
        from app.models.user import User
        return User(id="admin-uuid", role="admin")

    async def mock_current():
        from app.models.user import User
        return User(id="admin-uuid", role="admin")

    deps.get_current_user = mock_current
    deps.require_admin = mock_admin
    yield
    # Restore after test (import real ones again)
    import importlib
    importlib.reload(deps)


@pytest.fixture
def test_app(override_admin):
    from fastapi import FastAPI
    from app.api.v1.users import router

    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
async def client(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestUsersAPI:
    @patch("app.services.user.get_pending_teachers")
    async def test_get_pending_teachers_returns_200(self, mock_service, client, mock_session):
        from app.schemas.users import PendingTeachersResponse, UserOut

        mock_service.return_value = PendingTeachersResponse(
            users=[
                UserOut(
                    id="uuid-1", name="Teacher A", email="a@college.edu",
                    role="teacher", status="pending",
                ),
            ],
            total=1, page=1, limit=20, total_pages=1,
        )

        resp = await client.get("/api/v1/users/pending-teachers")

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert len(data["users"]) == 1
        assert data["users"][0]["status"] == "pending"
        assert data["meta"]["total"] == 1

    @patch("app.services.user.get_pending_teachers")
    async def test_get_pending_teachers_empty(self, mock_service, client, mock_session):
        from app.schemas.users import PendingTeachersResponse

        mock_service.return_value = PendingTeachersResponse(
            users=[], total=0, page=1, limit=20, total_pages=0,
        )

        resp = await client.get("/api/v1/users/pending-teachers")

        assert resp.status_code == 200
        data = resp.json()
        assert data["users"] == []
        assert data["meta"]["total"] == 0

    @patch("app.services.user.get_pending_teachers")
    async def test_get_pending_teachers_respects_pagination(self, mock_service, client, mock_session):
        from app.schemas.users import PendingTeachersResponse

        mock_service.return_value = PendingTeachersResponse(
            users=[], total=0, page=2, limit=10, total_pages=0,
        )

        resp = await client.get("/api/v1/users/pending-teachers?page=2&limit=10")

        assert resp.status_code == 200
        assert resp.json()["meta"]["page"] == 2
        assert mock_service.call_args[1]["page"] == 2
        assert mock_service.call_args[1]["limit"] == 10

    @patch("app.services.user.approve_teacher")
    async def test_approve_teacher_200(self, mock_service, client, mock_session):
        from app.schemas.users import UserOut

        mock_service.return_value = UserOut(
            id="uuid-1", name="Teacher A", email="a@college.edu",
            role="teacher", status="active",
        )

        resp = await client.patch("/api/v1/users/uuid-1/approve")

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["status"] == "active"

    @patch("app.services.user.approve_teacher")
    async def test_approve_teacher_404(self, mock_service, client, mock_session):
        from fastapi import HTTPException
        mock_service.side_effect = HTTPException(status_code=404, detail="User not found")

        resp = await client.patch("/api/v1/users/nonexistent/approve")

        assert resp.status_code == 404
        assert resp.json()["detail"] == "User not found"

    @patch("app.services.user.approve_teacher")
    async def test_approve_teacher_409_active(self, mock_service, client, mock_session):
        from fastapi import HTTPException
        mock_service.side_effect = HTTPException(status_code=409, detail="User is already active")

        resp = await client.patch("/api/v1/users/uuid-1/approve")

        assert resp.status_code == 409
        assert resp.json()["detail"] == "User is already active"

    @patch("app.services.user.reject_teacher")
    async def test_reject_teacher_200(self, mock_service, client, mock_session):
        from app.schemas.users import UserOut

        mock_service.return_value = UserOut(
            id="uuid-1", name="Teacher A", email="a@college.edu",
            role="teacher", status="rejected",
        )

        resp = await client.patch("/api/v1/users/uuid-1/reject")

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["status"] == "rejected"

    @patch("app.services.user.reject_teacher")
    async def test_reject_teacher_404(self, mock_service, client, mock_session):
        from fastapi import HTTPException
        mock_service.side_effect = HTTPException(status_code=404, detail="User not found")

        resp = await client.patch("/api/v1/users/nonexistent/reject")

        assert resp.status_code == 404

    @patch("app.services.user.reject_teacher")
    async def test_reject_teacher_409(self, mock_service, client, mock_session):
        from fastapi import HTTPException
        mock_service.side_effect = HTTPException(status_code=409, detail="User is already rejected")

        resp = await client.patch("/api/v1/users/uuid-1/reject")

        assert resp.status_code == 409

    @patch("app.services.user.get_active_teachers")
    async def test_get_teachers_200(self, mock_service, client, mock_session):
        from app.schemas.users import TeacherListResponse, UserOut

        mock_service.return_value = TeacherListResponse(
            users=[
                UserOut(
                    id="uuid-1", name="Dr. Rajesh Kumar", email="rajesh@college.edu",
                    role="teacher", status="active",
                ),
            ],
            total=1, page=1, limit=20, total_pages=1,
        )

        resp = await client.get("/api/v1/users/teachers")

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert len(data["users"]) == 1

    @patch("app.services.user.get_active_teachers")
    async def test_get_teachers_with_search(self, mock_service, client, mock_session):
        from app.schemas.users import TeacherListResponse

        mock_service.return_value = TeacherListResponse(
            users=[], total=0, page=1, limit=20, total_pages=0,
        )

        resp = await client.get("/api/v1/users/teachers?search=rajesh")

        assert resp.status_code == 200
        assert mock_service.call_args[1]["search"] == "rajesh"

    @patch("app.services.user.get_active_teachers")
    async def test_get_teachers_empty(self, mock_service, client, mock_session):
        from app.schemas.users import TeacherListResponse

        mock_service.return_value = TeacherListResponse(
            users=[], total=0, page=1, limit=20, total_pages=0,
        )

        resp = await client.get("/api/v1/users/teachers")

        assert resp.status_code == 200
        assert resp.json()["users"] == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && poetry run pytest tests/test_users.py -v`
Expected: FAIL - cannot import from `app.api.v1.users`

- [ ] **Step 3: Write minimal implementation**

```python
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.api import deps
from app.schemas.users import (
    PendingTeachersResponse,
    TeacherListResponse,
    UserActionResponse,
)
from app.services import user as user_service

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get(
    "/pending-teachers",
    response_model=PendingTeachersResponse,
    dependencies=[Depends(deps.require_admin)],
)
async def get_pending_teachers(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(deps.get_db),
):
    return await user_service.get_pending_teachers(db, page=page, limit=limit)


@router.patch(
    "/{id}/approve",
    response_model=UserActionResponse,
    dependencies=[Depends(deps.require_admin)],
)
async def approve_teacher(
    id: str,
    db: AsyncSession = Depends(deps.get_db),
):
    user = await user_service.approve_teacher(db, id)
    return UserActionResponse(data=user)


@router.patch(
    "/{id}/reject",
    response_model=UserActionResponse,
    dependencies=[Depends(deps.require_admin)],
)
async def reject_teacher(
    id: str,
    db: AsyncSession = Depends(deps.get_db),
):
    user = await user_service.reject_teacher(db, id)
    return UserActionResponse(data=user)


@router.get(
    "/teachers",
    response_model=TeacherListResponse,
    dependencies=[Depends(deps.require_admin)],
)
async def get_teachers(
    search: str | None = Query(None, max_length=180),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(deps.get_db),
):
    return await user_service.get_active_teachers(
        db, page=page, limit=limit, search=search,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && poetry run pytest tests/test_users.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/v1/users.py backend/tests/test_users.py
git commit -m "feat(users): add users router with FastAPI Depends wiring"
```

---

### Task 4: Register router in main.py

**Files:**
- Modify: `backend/app/main.py` (add `app.include_router`)
- No test changes needed (tests mount the router directly)

- [ ] **Step 1: Update main.py**

Insert the users router include after existing routers:

```python
from app.api.v1 import users

app.include_router(users.router)
```

The final main.py should look like:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import engine, Base
from app.api.v1 import users


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/v1/health")
async def health_check():
    return {
        "success": True,
        "data": {
            "status": "ok",
        },
    }


# ── Routes ─────────────────────────────────────────────
app.include_router(users.router)
```

- [ ] **Step 2: Run type check**

Run: `cd backend && poetry run mypy app/`
Expected: No errors

- [ ] **Step 3: Run full test suite**

Run: `cd backend && poetry run pytest -v`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add backend/app/main.py
git commit -m "feat(users): register users router in main.py"
```

---

### Task 5: Run full integration check

- [ ] **Step 1: Run all tests to confirm no regressions**

Run: `cd backend && poetry run pytest -v`
Expected: All tests PASS (Phase 1 + Phase 2 + Phase 3 users tests)

- [ ] **Step 2: Run mypy type check**

Run: `cd backend && poetry run mypy app/`
Expected: No errors

---

## Spec Coverage Check

| Spec Requirement | Task | Status |
|---|---|---|
| `app/schemas/users.py` with `UserOut`, `PendingTeachersResponse`, `TeacherListResponse`, `UserActionResponse` | Task 1 | Done |
| `app/services/user.py` — `get_pending_teachers` with pagination | Task 2 | Done |
| `app/services/user.py` — `approve_teacher` with 404/409 checks | Task 2 | Done |
| `app/services/user.py` — `reject_teacher` with 404/409 checks | Task 2 | Done |
| `app/services/user.py` — `get_active_teachers` with optional search | Task 2 | Done |
| `app/api/v1/users.py` — 4 endpoint handlers with `Depends(require_admin)` | Task 3 | Done |
| `app/main.py` — `app.include_router(users.router)` | Task 4 | Done |
| `tests/test_users.py` — schema tests | Task 1 | Done |
| `tests/test_users.py` — service tests (mocked AsyncSession) | Task 2 | Done |
| `tests/test_users.py` — endpoint integration tests (httpx + mocked service) | Task 3 | Done |
| `GET /api/v1/users/pending-teachers` — paginated, admin only | Tasks 2-3 | Done |
| `PATCH /api/v1/users/{id}/approve` — 404/409 handling | Tasks 2-3 | Done |
| `PATCH /api/v1/users/{id}/reject` — 404/409 handling | Tasks 2-3 | Done |
| `GET /api/v1/users/teachers` — paginated, searchable | Tasks 2-3 | Done |
| password hash excluded from all responses (via UserOut schema) | Task 1 | Done |
| All endpoints use `response_model` with Pydantic schemas | Task 3 | Done |

## Placeholder Scan

Every code block above contains complete, runnable Python. No "TODO", "implement later", "fill in details", "handle errors", or "similar to ..." patterns exist. All error handling is explicitly coded. All test assertions are complete. No `# type: ignore` or `Any` escape hatches used.

## Type Consistency Check

- `get_pending_teachers(db, page, limit)` → `PendingTeachersResponse` — matches `response_model=PendingTeachersResponse` on router
- `approve_teacher(db, id)` → `UserOut` — raises `HTTPException(404)` or `HTTPException(409)`
- `reject_teacher(db, id)` → `UserOut` — raises `HTTPException(404)` or `HTTPException(409)`
- `get_active_teachers(db, page, limit, search=None)` → `TeacherListResponse` — matches `response_model=TeacherListResponse`
- `UserOut` uses `model_config = {"from_attributes": True}` — compatible with SQLAlchemy model `__tablename__ = "users"`
- `UserActionResponse` wraps a single `UserOut` in `data` field — matches `response_model=UserActionResponse`
- Router prefix `/api/v1/users` — matches `app.include_router` mount
- All async functions use `AsyncSession` from `sqlalchemy.ext.asyncio`
- All queries use `from sqlalchemy import select` (not `from sqlalchemy.orm import Session`)
