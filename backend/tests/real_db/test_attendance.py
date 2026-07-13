from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models.attendance import Attendance, AttendanceStatus
from app.models.event import Event, EventStatus, EventType, EventCategory
from app.models.registration import Registration, RegistrationRole, RegistrationStatus

pytestmark = pytest.mark.asyncio


async def _setup_event_with_accepted_student(db, admin_user, teacher_user):
    future = datetime.now(timezone.utc) + timedelta(days=30)
    event = Event(
        title="Attendance Test",
        event_type=EventType.IN_COLLEGE,
        category=EventCategory.BOTH,
        status=EventStatus.APPROVED,
        venue="Auditorium",
        start_date=future,
        end_date=future + timedelta(hours=2),
        created_by=admin_user.id,
        coordinator_id=teacher_user.id,
    )
    db.add(event)
    await db.flush()

    reg = Registration(
        event_id=event.id,
        student_id=admin_user.id,
        role_type=RegistrationRole.PARTICIPANT,
        status=RegistrationStatus.ACCEPTED,
    )
    db.add(reg)
    await db.flush()

    return event


class TestAttendanceRealDB:

    async def test_mark_bulk_creates_records(self, db_session, admin_user, teacher_user):
        from app.services.attendance import AttendanceService

        event = await _setup_event_with_accepted_student(db_session, admin_user, teacher_user)
        today = date.today()

        result = await AttendanceService.mark_bulk(
            db_session, event.id, today,
            [{"studentId": admin_user.id, "present": True}],
            {"sub": str(teacher_user.id), "role": "teacher"},
        )

        assert result["count"] == 1

        rows = await db_session.execute(
            select(Attendance).where(
                Attendance.event_id == event.id,
                Attendance.attendance_date == today,
            )
        )
        records = rows.scalars().all()
        assert len(records) == 1
        assert records[0].status == AttendanceStatus.PRESENT
        assert records[0].student_id == admin_user.id
        assert records[0].marked_by == teacher_user.id

    async def test_mark_bulk_upsert(self, db_session, admin_user, teacher_user):
        from app.services.attendance import AttendanceService

        event = await _setup_event_with_accepted_student(db_session, admin_user, teacher_user)
        today = date.today()

        await AttendanceService.mark_bulk(
            db_session, event.id, today,
            [{"studentId": admin_user.id, "present": True}],
            {"sub": str(teacher_user.id), "role": "teacher"},
        )

        result2 = await AttendanceService.mark_bulk(
            db_session, event.id, today,
            [{"studentId": admin_user.id, "present": False}],
            {"sub": str(teacher_user.id), "role": "teacher"},
        )

        assert result2["count"] == 1

        rows = await db_session.execute(
            select(Attendance).where(
                Attendance.event_id == event.id,
                Attendance.student_id == admin_user.id,
                Attendance.attendance_date == today,
            )
        )
        records = rows.scalars().all()
        assert len(records) == 1
        assert records[0].status == AttendanceStatus.ABSENT

    async def test_get_event_attendance(self, db_session, admin_user, teacher_user):
        from app.services.attendance import AttendanceService

        event = await _setup_event_with_accepted_student(db_session, admin_user, teacher_user)
        today = date.today()

        await AttendanceService.mark_bulk(
            db_session, event.id, today,
            [{"studentId": admin_user.id, "present": True}],
            {"sub": str(teacher_user.id), "role": "teacher"},
        )

        records, total = await AttendanceService.get_event_attendance(
            db_session, event.id,
            {"sub": str(teacher_user.id), "role": "teacher"},
            page=1, limit=20,
        )

        assert total == 1
        assert len(records) == 1
        assert records[0].status == AttendanceStatus.PRESENT

    async def test_mark_bulk_event_not_found(self, db_session, teacher_user):
        from app.services.attendance import AttendanceService
        from app.core.exceptions import NotFoundException
        import uuid

        with pytest.raises(NotFoundException):
            await AttendanceService.mark_bulk(
                db_session, uuid.uuid4(), date.today(), [],
                {"sub": str(teacher_user.id), "role": "teacher"},
            )
