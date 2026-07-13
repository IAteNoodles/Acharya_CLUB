import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.models.user import User, Role, UserStatus

pytestmark = pytest.mark.asyncio


async def _create_pending_teacher(db, name="Teacher A"):
    user = User(
        name=name,
        email=f"teacher.{uuid.uuid4()}@college.edu",
        password_hash="hash",
        role=Role.TEACHER,
        status=UserStatus.PENDING,
    )
    db.add(user)
    await db.flush()
    return user


class TestUsersRealDB:

    async def test_get_pending_teachers_paginated(self, db_session):
        from app.services.user import get_pending_teachers

        await _create_pending_teacher(db_session, "Teacher A")
        await _create_pending_teacher(db_session, "Teacher B")

        active_teacher = User(
            name="Active Teacher",
            email=f"active.teacher.{uuid.uuid4()}@college.edu",
            password_hash="hash",
            role=Role.TEACHER,
            status=UserStatus.ACTIVE,
        )
        db_session.add(active_teacher)
        await db_session.flush()

        student = User(
            name="Student",
            email=f"student.{uuid.uuid4()}@college.edu",
            password_hash="hash",
            role=Role.STUDENT,
            status=UserStatus.ACTIVE,
        )
        db_session.add(student)
        await db_session.flush()

        result = await get_pending_teachers(db_session, page=1, limit=20)
        assert result.total == 2
        assert len(result.users) == 2
        assert all(u.status == "pending" for u in result.users)
        assert all(u.role == "teacher" for u in result.users)

    async def test_get_pending_teachers_empty(self, db_session):
        from app.services.user import get_pending_teachers

        result = await get_pending_teachers(db_session, page=1, limit=20)
        assert result.total == 0
        assert result.users == []

    async def test_approve_teacher_success(self, db_session):
        from app.services.user import approve_teacher

        teacher = await _create_pending_teacher(db_session)
        result = await approve_teacher(db_session, str(teacher.id))

        assert result.status == "active"

        row = await db_session.execute(
            select(User).where(User.id == teacher.id)
        )
        user = row.scalar_one()
        assert user.status == UserStatus.ACTIVE

    async def test_approve_teacher_not_found(self, db_session):
        from app.services.user import approve_teacher

        with pytest.raises(HTTPException) as exc:
            await approve_teacher(db_session, str(uuid.uuid4()))
        assert exc.value.status_code == 404

    async def test_approve_teacher_already_active(self, db_session):
        from app.services.user import approve_teacher

        teacher = User(
            name="Active Teacher",
            email=f"active.{uuid.uuid4()}@college.edu",
            password_hash="hash",
            role=Role.TEACHER,
            status=UserStatus.ACTIVE,
        )
        db_session.add(teacher)
        await db_session.flush()

        with pytest.raises(HTTPException) as exc:
            await approve_teacher(db_session, str(teacher.id))
        assert exc.value.status_code == 409
        assert "already active" in str(exc.value.detail).lower()

    async def test_reject_teacher_success(self, db_session):
        from app.services.user import reject_teacher

        teacher = await _create_pending_teacher(db_session)
        result = await reject_teacher(db_session, str(teacher.id))

        assert result.status == "rejected"

        row = await db_session.execute(
            select(User).where(User.id == teacher.id)
        )
        user = row.scalar_one()
        assert user.status == UserStatus.REJECTED

    async def test_reject_teacher_not_found(self, db_session):
        from app.services.user import reject_teacher

        with pytest.raises(HTTPException) as exc:
            await reject_teacher(db_session, str(uuid.uuid4()))
        assert exc.value.status_code == 404

    async def test_get_active_teachers_paginated(self, db_session):
        from app.services.user import get_active_teachers

        t1 = User(
            name="Dr. Rajesh",
            email=f"rajesh.{uuid.uuid4()}@college.edu",
            password_hash="hash",
            role=Role.TEACHER,
            status=UserStatus.ACTIVE,
        )
        db_session.add(t1)
        await db_session.flush()

        result = await get_active_teachers(db_session, page=1, limit=20)
        assert result.total >= 1
        assert any(u.name == "Dr. Rajesh" for u in result.users)
        assert all(u.status == "active" for u in result.users)
