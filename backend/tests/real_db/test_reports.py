import uuid
from datetime import datetime, timedelta, timezone
from datetime import date

import pytest

from app.models.attendance import Attendance, AttendanceStatus
from app.models.event import Event, EventStatus, EventType, EventCategory
from app.models.notification import Notification, NotificationType
from app.models.registration import Registration, RegistrationRole, RegistrationStatus
from app.models.user import User, Role, UserStatus

pytestmark = [pytest.mark.asyncio, pytest.mark.real_db]


class TestReportsRealDB:

    async def test_get_dashboard_stats(self, db_session, admin_user, teacher_user):
        from app.services.reports import ReportService

        student = User(
            name="Student",
            email=f"student.{uuid.uuid4()}@college.edu",
            password_hash="hash",
            role=Role.STUDENT,
            status=UserStatus.ACTIVE,
        )
        db_session.add(student)
        await db_session.flush()

        future = datetime.now(timezone.utc) + timedelta(days=30)
        event = Event(
            title="Report Event",
            event_type=EventType.IN_COLLEGE,
            category=EventCategory.BOTH,
            status=EventStatus.APPROVED,
            venue="Auditorium",
            start_date=future,
            end_date=future + timedelta(hours=2),
            created_by=admin_user.id,
            coordinator_id=teacher_user.id,
        )
        db_session.add(event)
        await db_session.flush()

        reg = Registration(
            event_id=event.id,
            student_id=student.id,
            role_type=RegistrationRole.PARTICIPANT,
            status=RegistrationStatus.ACCEPTED,
        )
        db_session.add(reg)
        await db_session.flush()

        att = Attendance(
            event_id=event.id,
            student_id=student.id,
            marked_by=teacher_user.id,
            attendance_date=date.today(),
            status=AttendanceStatus.PRESENT,
        )
        db_session.add(att)
        await db_session.flush()

        notif = Notification(
            user_id=student.id,
            type=NotificationType.REGISTRATION_ACCEPTED,
            title="Welcome",
            message="You are accepted",
        )
        db_session.add(notif)
        await db_session.flush()

        result = await ReportService.get_dashboard_stats(db_session)

        assert result.users.total >= 3, f"by_role={result.users.by_role}"
        assert result.users.by_role.get("admin") >= 1, str(result.users.by_role)
        assert result.users.by_role.get("teacher") >= 1, str(result.users.by_role)
        assert result.users.by_role.get("student") >= 1, str(result.users.by_role)

        assert result.events.total >= 1
        assert any("approved" in k.lower() for k in result.events.by_status)

        assert result.registrations.total >= 1
        assert any("accepted" in k.lower() for k in result.registrations.by_status)

        assert result.attendance.total >= 1
        assert any("present" in k.lower() for k in result.attendance.by_status)

        assert result.notifications.total >= 1
        assert result.notifications.unread >= 1

    async def test_get_dashboard_stats_empty_db(self, db_session):
        from app.services.reports import ReportService

        result = await ReportService.get_dashboard_stats(db_session)

        assert result.users.total == 0
        assert result.users.by_role == {}
        assert result.events.total == 0
        assert result.registrations.total == 0
        assert result.attendance.total == 0
        assert result.notifications.total == 0
        assert result.notifications.unread == 0
