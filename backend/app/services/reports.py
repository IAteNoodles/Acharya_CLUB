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


def _enum_key(value) -> str:
    return value.value if hasattr(value, 'value') else str(value)


def _grouped_counts(rows) -> dict:
    return {_enum_key(r[0]): r[1] for r in rows}


def _cross_counts(rows) -> dict:
    counts: dict = {}
    for outer, inner, n in rows:
        counts.setdefault(_enum_key(outer), {})[_enum_key(inner)] = n
    return counts


def _collapse_outer(cross: dict) -> dict:
    return {outer: sum(inner.values()) for outer, inner in cross.items()}


def _collapse_inner(cross: dict) -> dict:
    counts: dict = {}
    for inner_counts in cross.values():
        for key, n in inner_counts.items():
            counts[key] = counts.get(key, 0) + n
    return counts


def _total_from_counts(counts: dict) -> int:
    return sum(counts.values())


class ReportService:

    @staticmethod
    async def get_dashboard_stats(db: AsyncSession) -> DashboardResponse:
        async def count_users_by_role_status():
            r = await db.execute(
                select(User.role, User.status, func.count()).group_by(User.role, User.status)
            )
            return _cross_counts(r.all())

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

        users_by_role_status = await count_users_by_role_status()
        users_by_role = _collapse_outer(users_by_role_status)
        users_by_status = _collapse_inner(users_by_role_status)
        events_by_status = await count_events_by_status()
        events_by_type = await count_events_by_type()
        regs_by_status = await count_registrations_by_status()
        att_by_status = await count_attendance_by_status()
        notif_total = await count_notifications_total()
        notif_unread = await count_notifications_unread()

        return DashboardResponse(
            users=UserStats(
                total=_total_from_counts(users_by_role),
                by_role=users_by_role,
                by_status=users_by_status,
                by_role_status=users_by_role_status,
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
