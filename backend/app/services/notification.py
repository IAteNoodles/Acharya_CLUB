import uuid
from typing import Optional
from sqlalchemy import select, func
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
    context: Optional[dict] = None,
) -> tuple[str, str]:
    context = context or {}
    title, msg_fn = NOTIFICATION_TEMPLATES[notif_type]
    return title, msg_fn(context)


class NotificationService:

    @staticmethod
    async def create_notification(
        db: AsyncSession,
        user_id: uuid.UUID,
        notif_type: NotificationType,
        title: str,
        message: str,
        entity_type: Optional[str] = None,
        entity_id: Optional[uuid.UUID] = None,
    ) -> Notification:
        notif = Notification(
            user_id=user_id,
            type=notif_type,
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
        from sqlalchemy import update
        stmt = (
            update(Notification)
            .where(Notification.user_id == user_id, Notification.is_read == False)
            .values(is_read=True)
        )
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount

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
