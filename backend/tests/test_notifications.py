import uuid
from unittest.mock import AsyncMock, MagicMock
import pytest
from sqlalchemy import select, func

USER_ID = uuid.uuid4()
OTHER_USER_ID = uuid.uuid4()
NOTIF_ID = uuid.uuid4()


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
            db, user_id=USER_ID, notif_type="registration_accepted",
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
        db.scalar.return_value = 1

        notifs, total = await NotificationService.get_user_notifications(
            db, user_id=USER_ID, page=1, limit=20,
        )

        assert len(notifs) == 1
        assert total == 1

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
        result_mock = MagicMock()
        result_mock.rowcount = 2
        db.execute.return_value = result_mock

        count = await NotificationService.mark_all_as_read(db, USER_ID)

        assert count == 2
        db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_mark_all_as_read_other_user_unaffected(self):
        from app.services.notification import NotificationService

        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.rowcount = 0
        db.execute.return_value = result_mock

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
