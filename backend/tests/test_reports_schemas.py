import pytest
from pydantic import ValidationError


class TestUserStats:
    def test_valid(self):
        from app.schemas.reports import UserStats

        data = UserStats(
            total=100,
            by_role={"student": 80, "teacher": 20},
            by_status={"active": 90, "pending": 10},
            by_role_status={"student": {"active": 76, "pending": 4}, "teacher": {"active": 14, "pending": 6}},
        )
        assert data.total == 100
        assert data.by_role["student"] == 80
        assert data.by_role_status["teacher"]["pending"] == 6

    def test_rejects_missing_fields(self):
        from app.schemas.reports import UserStats

        with pytest.raises(ValidationError):
            UserStats()

    def test_rejects_missing_by_role_status(self):
        from app.schemas.reports import UserStats

        with pytest.raises(ValidationError):
            UserStats(total=100, by_role={}, by_status={})


class TestEventStats:
    def test_valid(self):
        from app.schemas.reports import EventStats

        data = EventStats(total=50, by_status={"approved": 30, "pending": 20}, by_type={"in_college": 40, "out_college": 10})
        assert data.total == 50


class TestRegistrationStats:
    def test_valid(self):
        from app.schemas.reports import RegistrationStats

        data = RegistrationStats(total=200, by_status={"accepted": 150, "pending": 30, "rejected": 20})
        assert data.total == 200


class TestAttendanceStats:
    def test_valid(self):
        from app.schemas.reports import AttendanceStats

        data = AttendanceStats(total=500, by_status={"present": 400, "absent": 80, "late": 20})
        assert data.total == 500


class TestNotificationStats:
    def test_valid(self):
        from app.schemas.reports import NotificationStats

        data = NotificationStats(total=300, unread=45)
        assert data.total == 300
        assert data.unread == 45


class TestDashboardResponse:
    def test_valid(self):
        from app.schemas.reports import DashboardResponse, UserStats, EventStats, RegistrationStats, AttendanceStats, NotificationStats

        data = DashboardResponse(
            users=UserStats(total=100, by_role={}, by_status={}, by_role_status={}),
            events=EventStats(total=50, by_status={}, by_type={}),
            registrations=RegistrationStats(total=200, by_status={}),
            attendance=AttendanceStats(total=500, by_status={}),
            notifications=NotificationStats(total=300, unread=45),
        )
        assert data.users.total == 100
        assert data.events.total == 50
        assert data.registrations.total == 200
        assert data.attendance.total == 500
        assert data.notifications.total == 300

    def test_rejects_missing_section(self):
        from app.schemas.reports import DashboardResponse, UserStats, EventStats, RegistrationStats, AttendanceStats

        with pytest.raises(ValidationError):
            DashboardResponse(
                users=UserStats(total=100, by_role={}, by_status={}, by_role_status={}),
                events=EventStats(total=50, by_status={}, by_type={}),
                registrations=RegistrationStats(total=200, by_status={}),
                attendance=AttendanceStats(total=500, by_status={}),
            )
