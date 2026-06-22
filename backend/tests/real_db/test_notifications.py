import uuid

import pytest
from sqlalchemy import select

from app.models.notification import Notification, NotificationType

pytestmark = pytest.mark.asyncio


class TestNotificationsRealDB:

    async def test_create_notification(self, db_session, student_user):
        from app.services.notification import NotificationService

        notif = await NotificationService.create_notification(
            db_session,
            user_id=student_user.id,
            notif_type=NotificationType.REGISTRATION_ACCEPTED,
            title="Accepted",
            message="You are accepted",
            entity_type="registration",
            entity_id=uuid.uuid4(),
        )

        assert notif.user_id == student_user.id
        assert notif.type == NotificationType.REGISTRATION_ACCEPTED
        assert notif.is_read is False

        row = await db_session.execute(
            select(Notification).where(Notification.id == notif.id)
        )
        db_notif = row.scalar_one()
        assert db_notif.title == "Accepted"
        assert db_notif.message == "You are accepted"

    async def test_get_user_notifications_paginated(self, db_session, student_user):
        from app.services.notification import NotificationService

        for i in range(3):
            await NotificationService.create_notification(
                db_session,
                user_id=student_user.id,
                notif_type=NotificationType.REGISTRATION_ACCEPTED,
                title=f"Notification {i}",
                message=f"Message {i}",
            )

        notifs, total = await NotificationService.get_user_notifications(
            db_session, user_id=student_user.id, page=1, limit=10,
        )

        assert total == 3
        assert len(notifs) == 3

        notifs_p2, total_p2 = await NotificationService.get_user_notifications(
            db_session, user_id=student_user.id, page=1, limit=2,
        )
        assert total_p2 == 3
        assert len(notifs_p2) == 2

    async def test_get_user_notifications_unread_only(self, db_session, student_user):
        from app.services.notification import NotificationService

        await NotificationService.create_notification(
            db_session,
            user_id=student_user.id,
            notif_type=NotificationType.REGISTRATION_ACCEPTED,
            title="Unread 1",
            message="Msg 1",
        )
        n2 = await NotificationService.create_notification(
            db_session,
            user_id=student_user.id,
            notif_type=NotificationType.REGISTRATION_REJECTED,
            title="Unread 2",
            message="Msg 2",
        )
        await NotificationService.mark_as_read(db_session, n2.id, student_user.id)

        notifs, total = await NotificationService.get_user_notifications(
            db_session, user_id=student_user.id, page=1, limit=10, unread_only=True,
        )

        assert total == 1
        assert len(notifs) == 1
        assert notifs[0].title == "Unread 1"

    async def test_get_user_notifications_other_user_empty(self, db_session, student_user):
        from app.services.notification import NotificationService

        await NotificationService.create_notification(
            db_session,
            user_id=student_user.id,
            notif_type=NotificationType.REGISTRATION_ACCEPTED,
            title="Test",
            message="Test",
        )

        other_id = uuid.uuid4()
        notifs, total = await NotificationService.get_user_notifications(
            db_session, user_id=other_id, page=1, limit=10,
        )

        assert total == 0
        assert notifs == []

    async def test_mark_as_read(self, db_session, student_user):
        from app.services.notification import NotificationService

        notif = await NotificationService.create_notification(
            db_session,
            user_id=student_user.id,
            notif_type=NotificationType.REGISTRATION_ACCEPTED,
            title="Read Me",
            message="Please read",
        )

        result = await NotificationService.mark_as_read(
            db_session, notif.id, student_user.id,
        )

        assert result.is_read is True

        row = await db_session.execute(
            select(Notification).where(Notification.id == notif.id)
        )
        db_notif = row.scalar_one()
        assert db_notif.is_read is True

    async def test_mark_as_read_not_found(self, db_session, student_user):
        from app.services.notification import NotificationService
        from app.core.exceptions import NotFoundException

        with pytest.raises(NotFoundException):
            await NotificationService.mark_as_read(
                db_session, uuid.uuid4(), student_user.id,
            )

    async def test_mark_as_read_wrong_user(self, db_session, student_user):
        from app.services.notification import NotificationService
        from app.core.exceptions import ForbiddenException

        notif = await NotificationService.create_notification(
            db_session,
            user_id=student_user.id,
            notif_type=NotificationType.REGISTRATION_ACCEPTED,
            title="Mine",
            message="Only I can read",
        )

        other_id = uuid.uuid4()
        with pytest.raises(ForbiddenException):
            await NotificationService.mark_as_read(
                db_session, notif.id, other_id,
            )

    async def test_mark_all_as_read(self, db_session, student_user):
        from app.services.notification import NotificationService

        for i in range(3):
            await NotificationService.create_notification(
                db_session,
                user_id=student_user.id,
                notif_type=NotificationType.REGISTRATION_ACCEPTED,
                title=f"Bulk {i}",
                message=f"Msg {i}",
            )

        count = await NotificationService.mark_all_as_read(db_session, student_user.id)
        assert count == 3

        rows = await db_session.execute(
            select(Notification).where(
                Notification.user_id == student_user.id,
                Notification.is_read == False,
            )
        )
        unread = rows.scalars().all()
        assert len(unread) == 0

    async def test_get_unread_count(self, db_session, student_user):
        from app.services.notification import NotificationService

        for i in range(2):
            await NotificationService.create_notification(
                db_session,
                user_id=student_user.id,
                notif_type=NotificationType.REGISTRATION_ACCEPTED,
                title=f"Unread {i}",
                message=f"Msg {i}",
            )

        count = await NotificationService.get_unread_count(db_session, student_user.id)
        assert count == 2
