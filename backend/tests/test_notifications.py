import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
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
        from unittest.mock import MagicMock

        db = AsyncMock()
        db.add = MagicMock()  # add() is synchronous on AsyncSession

        notif = await NotificationService.create_notification(
            db, user_id=USER_ID, notif_type="registration_accepted",
            title="Accepted", message="You are accepted",
            entity_type="registration", entity_id=uuid.uuid4(),
        )

        db.add.assert_called_once()
        db.flush.assert_called_once()
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
        app.include_router(router, prefix="/api/v1/notifications")
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
        app.include_router(router, prefix="/api/v1/notifications")
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
        app.include_router(router, prefix="/api/v1/notifications")
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
        app.include_router(router, prefix="/api/v1/notifications")
        app.dependency_overrides[get_current_user] = lambda: self.student_user

        from app.services.notification import NotificationService

        mock_notif = MagicMock()
        mock_notif.id = NOTIF_ID
        mock_notif.user_id = USER_ID
        mock_notif.type = "registration_accepted"
        mock_notif.title = "Accepted"
        mock_notif.message = "You are accepted"
        mock_notif.is_read = True
        mock_notif.created_at = datetime(2026, 6, 21, 10, 0, 0)
        mock_notif.related_entity_type = None
        mock_notif.related_entity_id = None

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
        from app.core.exceptions import NotFoundException, register_exception_handlers

        app = FastAPI()
        app.include_router(router, prefix="/api/v1/notifications")
        register_exception_handlers(app)
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
        app.include_router(router, prefix="/api/v1/notifications")
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

        app = FastAPI()
        app.include_router(router, prefix="/api/v1/notifications")

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/notifications")

        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_mark_read_unauthorized(self):
        from fastapi import FastAPI
        from app.api.v1.notifications import router

        app = FastAPI()
        app.include_router(router, prefix="/api/v1/notifications")

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.patch(f"/api/v1/notifications/{NOTIF_ID}/read")

        assert resp.status_code == 401


class TestRegistrationNotificationIntegration:

    @pytest.mark.asyncio
    async def test_accept_registration_creates_notification(self):
        from app.services.registration import RegistrationService
        from app.services.notification import NotificationService

        coordinator_id = uuid.uuid4()
        db = AsyncMock()
        mock_reg = MagicMock()
        mock_reg.status = "pending"
        mock_reg.student_id = USER_ID
        mock_reg.event_id = uuid.uuid4()
        mock_reg.role_type = "volunteer"

        mock_event = MagicMock()
        mock_event.title = "Tech Fest"
        mock_event.coordinator_id = coordinator_id

        db.get = AsyncMock(side_effect=[mock_reg, mock_event])

        with patch.object(NotificationService, "create_notification", new=AsyncMock()) as mock_create:
            await RegistrationService.accept_registration(
                db, NOTIF_ID,
                {"sub": str(coordinator_id), "role": "teacher"},
            )

        mock_create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_reject_registration_creates_notification(self):
        from app.services.registration import RegistrationService
        from app.services.notification import NotificationService

        coordinator_id = uuid.uuid4()
        db = AsyncMock()
        mock_reg = MagicMock()
        mock_reg.status = "pending"
        mock_reg.student_id = USER_ID
        mock_reg.event_id = uuid.uuid4()
        mock_reg.role_type = "volunteer"

        mock_event = MagicMock()
        mock_event.title = "Tech Fest"
        mock_event.coordinator_id = coordinator_id

        db.get = AsyncMock(side_effect=[mock_reg, mock_event])

        with patch.object(NotificationService, "create_notification", new=AsyncMock()) as mock_create:
            await RegistrationService.reject_registration(
                db, NOTIF_ID,
                {"sub": str(coordinator_id), "role": "teacher"},
            )

        mock_create.assert_awaited_once()


class TestEventNotificationIntegration:

    @pytest.mark.asyncio
    async def test_approve_event_creates_notification(self):
        from app.services.event import EventService
        from app.services.notification import NotificationService

        coordinator_id = uuid.uuid4()
        db = AsyncMock()
        mock_event = MagicMock()
        mock_event.status = "pending"
        mock_event.created_by = USER_ID
        mock_event.coordinator_id = coordinator_id
        mock_event.title = "Tech Fest"
        mock_event.id = uuid.uuid4()

        db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=mock_event))

        with patch.object(NotificationService, "create_notification", new=AsyncMock()) as mock_create:
            await EventService.approve_event(
                db, str(uuid.uuid4()), None,
                {"sub": str(coordinator_id), "role": "teacher"},
            )

        mock_create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_reject_event_creates_notification(self):
        from app.services.event import EventService
        from app.services.notification import NotificationService

        coordinator_id = uuid.uuid4()
        db = AsyncMock()
        mock_event = MagicMock()
        mock_event.status = "pending"
        mock_event.created_by = USER_ID
        mock_event.coordinator_id = coordinator_id
        mock_event.title = "Tech Fest"
        mock_event.id = uuid.uuid4()

        db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=mock_event))

        with patch.object(NotificationService, "create_notification", new=AsyncMock()) as mock_create:
            await EventService.reject_event(
                db, str(uuid.uuid4()), "Not suitable",
                {"sub": str(coordinator_id), "role": "teacher"},
            )

        mock_create.assert_awaited_once()


class TestTeacherNotificationIntegration:

    @pytest.mark.asyncio
    async def test_approve_teacher_creates_notification(self):
        from app.services.user import approve_teacher
        from app.services.notification import NotificationService

        db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = str(USER_ID)
        mock_user.role = "teacher"
        mock_user.status = "pending"
        mock_user.name = "John"
        mock_user.email = "john@college.edu"
        mock_user.created_at = MagicMock()
        mock_user.updated_at = MagicMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_result.scalar_one.return_value = mock_user
        db.execute.return_value = mock_result

        with patch.object(NotificationService, "create_notification", new=AsyncMock()) as mock_create:
            await approve_teacher(db, str(USER_ID))

        mock_create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_reject_teacher_creates_notification(self):
        from app.services.user import reject_teacher
        from app.services.notification import NotificationService

        db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = str(USER_ID)
        mock_user.role = "teacher"
        mock_user.status = "pending"
        mock_user.name = "John"
        mock_user.email = "john@college.edu"
        mock_user.created_at = MagicMock()
        mock_user.updated_at = MagicMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_result.scalar_one.return_value = mock_user
        db.execute.return_value = mock_result

        with patch.object(NotificationService, "create_notification", new=AsyncMock()) as mock_create:
            await reject_teacher(db, str(USER_ID))

        mock_create.assert_awaited_once()
