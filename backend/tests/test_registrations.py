import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError
from httpx import ASGITransport, AsyncClient

from app.api import deps
from app.core.exceptions import ConflictException, ForbiddenException, NotFoundException
from app.models.registration import RegistrationRole, RegistrationStatus

STUDENT_ID = uuid.uuid4()
TEACHER_ID = uuid.uuid4()
EVENT_ID = uuid.uuid4()
REG_ID = uuid.uuid4()


class TestRegistrationSchemas:
    def test_register_request_valid(self):
        from app.schemas.registration import RegisterRequest

        data = RegisterRequest(event_id=EVENT_ID, role_type="participant")
        assert data.event_id == EVENT_ID
        assert data.role_type == RegistrationRole.PARTICIPANT

    def test_register_request_valid_volunteer(self):
        from app.schemas.registration import RegisterRequest

        data = RegisterRequest(event_id=EVENT_ID, role_type="volunteer")
        assert data.role_type == RegistrationRole.VOLUNTEER

    def test_register_request_rejects_invalid_role(self):
        from app.schemas.registration import RegisterRequest

        with pytest.raises(ValidationError):
            RegisterRequest(event_id=EVENT_ID, role_type="invalid")

class TestRegistrationService:
    @pytest.mark.asyncio
    async def test_register_success(self):
        from app.services.registration import RegistrationService

        db = AsyncMock()
        mock_event = MagicMock()
        mock_event.status = "approved"
        mock_event.coordinator_id = uuid.uuid4()
        mock_event.category = "participant"
        mock_event.max_registrations = 0
        db.get.return_value = mock_event
        db.execute.return_value = MagicMock(scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=None))))

        reg = await RegistrationService.register(
            db, EVENT_ID, "participant",
            {"sub": str(STUDENT_ID), "role": "student"},
        )

        db.add.assert_called_once()
        db.commit.assert_called_once()
        db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_event_not_found(self):
        from app.services.registration import RegistrationService

        db = AsyncMock()
        db.get.return_value = None

        with pytest.raises(NotFoundException):
            await RegistrationService.register(
                db, EVENT_ID, "participant",
                {"sub": str(STUDENT_ID), "role": "student"},
            )

    @pytest.mark.asyncio
    async def test_register_event_not_approved(self):
        from app.services.registration import RegistrationService

        db = AsyncMock()
        mock_event = MagicMock()
        mock_event.status = "draft"
        mock_event.coordinator_id = uuid.uuid4()
        db.get.return_value = mock_event

        with pytest.raises(ConflictException, match="not open for registration"):
            await RegistrationService.register(
                db, EVENT_ID, "participant",
                {"sub": str(STUDENT_ID), "role": "student"},
            )

    @pytest.mark.asyncio
    async def test_register_no_coordinator(self):
        from app.services.registration import RegistrationService

        db = AsyncMock()
        mock_event = MagicMock()
        mock_event.status = "approved"
        mock_event.coordinator_id = None
        db.get.return_value = mock_event

        with pytest.raises(ConflictException, match="no coordinator assigned"):
            await RegistrationService.register(
                db, EVENT_ID, "participant",
                {"sub": str(STUDENT_ID), "role": "student"},
            )

    @pytest.mark.asyncio
    async def test_register_duplicate(self):
        from app.services.registration import RegistrationService

        db = AsyncMock()
        mock_event = MagicMock()
        mock_event.status = "approved"
        mock_event.coordinator_id = uuid.uuid4()
        mock_event.category = "both"
        mock_event.max_registrations = 0
        db.get.return_value = mock_event
        db.execute.return_value = MagicMock(scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=MagicMock()))))

        with pytest.raises(ConflictException, match="Already registered"):
            await RegistrationService.register(
                db, EVENT_ID, "participant",
                {"sub": str(STUDENT_ID), "role": "student"},
            )

    @pytest.mark.asyncio
    async def test_register_duplicate_even_with_other_role(self):
        from app.services.registration import RegistrationService

        db = AsyncMock()
        mock_event = MagicMock()
        mock_event.status = "approved"
        mock_event.coordinator_id = uuid.uuid4()
        mock_event.category = "both"
        mock_event.max_registrations = 0
        db.get.return_value = mock_event
        existing = MagicMock()
        existing.role_type = RegistrationRole.PARTICIPANT
        db.execute.return_value = MagicMock(scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=existing))))

        with pytest.raises(ConflictException, match="Already registered"):
            await RegistrationService.register(
                db, EVENT_ID, "volunteer",
                {"sub": str(STUDENT_ID), "role": "student"},
            )

    @pytest.mark.asyncio
    async def test_register_role_not_accepted_by_category(self):
        from app.services.registration import RegistrationService

        db = AsyncMock()
        mock_event = MagicMock()
        mock_event.status = "approved"
        mock_event.coordinator_id = uuid.uuid4()
        mock_event.category = "participant"
        db.get.return_value = mock_event

        with pytest.raises(ConflictException, match="only accepts participant"):
            await RegistrationService.register(
                db, EVENT_ID, "volunteer",
                {"sub": str(STUDENT_ID), "role": "student"},
            )
        db.execute.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_register_both_category_accepts_either_role(self):
        from app.services.registration import RegistrationService

        db = AsyncMock()
        mock_event = MagicMock()
        mock_event.status = "approved"
        mock_event.coordinator_id = uuid.uuid4()
        mock_event.category = "both"
        mock_event.max_registrations = 0
        db.get.return_value = mock_event
        db.execute.return_value = MagicMock(scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=None))))

        await RegistrationService.register(
            db, EVENT_ID, "volunteer",
            {"sub": str(STUDENT_ID), "role": "student"},
        )

        db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_student_registrations_paginated(self):
        from app.services.registration import RegistrationService

        db = AsyncMock()
        count_result = MagicMock()
        count_result.scalar_one.return_value = 0
        data_result = MagicMock()
        data_result.scalars.return_value = MagicMock(all=MagicMock(return_value=[]))
        db.execute = AsyncMock(side_effect=[count_result, data_result])

        registrations, total = await RegistrationService.get_student_registrations(
            db, str(STUDENT_ID),
        )

        assert total == 0
        assert registrations == []

    @pytest.mark.asyncio
    async def test_get_event_registrations_success(self):
        from app.services.registration import RegistrationService

        db = AsyncMock()
        mock_event = MagicMock()
        mock_event.coordinator_id = uuid.UUID(str(TEACHER_ID))
        db.get.return_value = mock_event
        count_result = MagicMock()
        count_result.scalar_one.return_value = 0
        data_result = MagicMock()
        data_result.scalars.return_value = MagicMock(all=MagicMock(return_value=[]))
        db.execute = AsyncMock(side_effect=[count_result, data_result])

        registrations, total = await RegistrationService.get_event_registrations(
            db, EVENT_ID, {"sub": str(TEACHER_ID), "role": "teacher"},
        )

        assert total == 0

    @pytest.mark.asyncio
    async def test_get_event_registrations_forbidden(self):
        from app.services.registration import RegistrationService

        db = AsyncMock()
        mock_event = MagicMock()
        mock_event.coordinator_id = uuid.uuid4()
        db.get.return_value = mock_event

        with pytest.raises(ForbiddenException):
            await RegistrationService.get_event_registrations(
                db, EVENT_ID, {"sub": str(STUDENT_ID), "role": "student"},
                status_filter=None, page=1, limit=20,
            )

    @pytest.mark.asyncio
    async def test_get_event_registrations_admin_bypass(self):
        from app.services.registration import RegistrationService

        db = AsyncMock()
        mock_event = MagicMock()
        mock_event.coordinator_id = uuid.uuid4()
        db.get.return_value = mock_event
        count_result = MagicMock()
        count_result.scalar_one.return_value = 0
        data_result = MagicMock()
        data_result.scalars.return_value = MagicMock(all=MagicMock(return_value=[]))
        db.execute = AsyncMock(side_effect=[count_result, data_result])

        registrations, total = await RegistrationService.get_event_registrations(
            db, EVENT_ID, {"sub": str(uuid.uuid4()), "role": "admin"},
        )

        assert total == 0

    @pytest.mark.asyncio
    async def test_accept_registration_success(self):
        from app.services.registration import RegistrationService

        db = AsyncMock()
        mock_reg = MagicMock()
        mock_reg.status = RegistrationStatus.PENDING
        mock_reg.event_id = EVENT_ID
        mock_event = MagicMock()
        mock_event.coordinator_id = uuid.UUID(str(TEACHER_ID))
        mock_event.max_registrations = 0
        db.get.side_effect = [mock_reg, mock_event]

        reg = await RegistrationService.accept_registration(
            db, REG_ID, {"sub": str(TEACHER_ID), "role": "teacher"},
        )

        assert reg.status == RegistrationStatus.ACCEPTED
        assert db.commit.call_count == 2
        assert db.refresh.call_count == 2

    @pytest.mark.asyncio
    async def test_accept_registration_capacity_reached(self):
        from app.services.registration import RegistrationService

        db = AsyncMock()
        mock_reg = MagicMock()
        mock_reg.status = RegistrationStatus.PENDING
        mock_reg.event_id = EVENT_ID
        mock_event = MagicMock()
        mock_event.coordinator_id = uuid.UUID(str(TEACHER_ID))
        mock_event.max_registrations = 2
        db.get.side_effect = [mock_reg, mock_event]
        count_result = MagicMock()
        count_result.scalar_one.return_value = 2
        db.execute.return_value = count_result

        with pytest.raises(ConflictException, match="maximum registration capacity"):
            await RegistrationService.accept_registration(
                db, REG_ID, {"sub": str(TEACHER_ID), "role": "teacher"},
            )
        assert mock_reg.status == RegistrationStatus.PENDING

    @pytest.mark.asyncio
    async def test_accept_registration_forbidden_not_coordinator(self):
        from app.services.registration import RegistrationService

        db = AsyncMock()
        mock_reg = MagicMock()
        mock_reg.status = RegistrationStatus.PENDING
        mock_reg.event_id = EVENT_ID
        mock_event = MagicMock()
        mock_event.coordinator_id = uuid.uuid4()
        db.get.side_effect = [mock_reg, mock_event]

        with pytest.raises(ForbiddenException, match="not the coordinator"):
            await RegistrationService.accept_registration(
                db, REG_ID, {"sub": str(TEACHER_ID), "role": "teacher"},
            )

    @pytest.mark.asyncio
    async def test_reject_registration_not_found(self):
        from app.services.registration import RegistrationService

        db = AsyncMock()
        db.get.return_value = None

        with pytest.raises(NotFoundException, match="Registration not found"):
            await RegistrationService.reject_registration(
                db, REG_ID, {"sub": str(TEACHER_ID), "role": "teacher"},
            )

    @pytest.mark.asyncio
    async def test_reject_registration_forbidden_not_coordinator(self):
        from app.services.registration import RegistrationService

        db = AsyncMock()
        mock_reg = MagicMock()
        mock_reg.status = RegistrationStatus.PENDING
        mock_reg.event_id = EVENT_ID
        mock_event = MagicMock()
        mock_event.coordinator_id = uuid.uuid4()
        db.get.side_effect = [mock_reg, mock_event]

        with pytest.raises(ForbiddenException, match="not the coordinator"):
            await RegistrationService.reject_registration(
                db, REG_ID, {"sub": str(TEACHER_ID), "role": "teacher"},
            )

    @pytest.mark.asyncio
    async def test_accept_registration_not_found(self):
        from app.services.registration import RegistrationService

        db = AsyncMock()
        db.get.return_value = None

        with pytest.raises(NotFoundException):
            await RegistrationService.accept_registration(
                db, REG_ID, {"sub": str(TEACHER_ID), "role": "teacher"},
            )

    @pytest.mark.asyncio
    async def test_accept_registration_not_pending(self):
        from app.services.registration import RegistrationService

        db = AsyncMock()
        mock_reg = MagicMock()
        mock_reg.status = RegistrationStatus.ACCEPTED
        mock_reg.event_id = EVENT_ID
        mock_event = MagicMock()
        mock_event.coordinator_id = uuid.UUID(str(TEACHER_ID))
        db.get.side_effect = [mock_reg, mock_event]

        with pytest.raises(ConflictException, match="not in pending status"):
            await RegistrationService.accept_registration(
                db, REG_ID, {"sub": str(TEACHER_ID), "role": "teacher"},
            )

    @pytest.mark.asyncio
    async def test_reject_registration_success(self):
        from app.services.registration import RegistrationService

        db = AsyncMock()
        mock_reg = MagicMock()
        mock_reg.status = RegistrationStatus.PENDING
        mock_reg.event_id = EVENT_ID
        mock_event = MagicMock()
        mock_event.coordinator_id = uuid.UUID(str(TEACHER_ID))
        db.get.side_effect = [mock_reg, mock_event]

        reg = await RegistrationService.reject_registration(
            db, REG_ID, {"sub": str(TEACHER_ID), "role": "teacher"},
        )

        assert reg.status == RegistrationStatus.REJECTED

    @pytest.mark.asyncio
    async def test_register_max_capacity_reached(self):
        from app.services.registration import RegistrationService

        db = AsyncMock()
        mock_event = MagicMock()
        mock_event.status = "approved"
        mock_event.coordinator_id = uuid.uuid4()
        mock_event.category = "participant"
        mock_event.max_registrations = 2
        db.get.return_value = mock_event
        count_result = MagicMock()
        count_result.scalar_one.return_value = 2
        db.execute = AsyncMock(side_effect=[count_result, MagicMock(scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=None))))])

        with pytest.raises(ConflictException, match="maximum registration capacity"):
            await RegistrationService.register(
                db, EVENT_ID, "participant",
                {"sub": str(STUDENT_ID), "role": "student"},
            )

    @pytest.mark.asyncio
    async def test_get_student_registrations_with_status_filter(self):
        from app.services.registration import RegistrationService

        db = AsyncMock()
        count_result = MagicMock()
        count_result.scalar_one.return_value = 0
        data_result = MagicMock()
        data_result.scalars.return_value = MagicMock(all=MagicMock(return_value=[]))
        db.execute = AsyncMock(side_effect=[count_result, data_result])

        registrations, total = await RegistrationService.get_student_registrations(
            db, str(STUDENT_ID), status_filter="accepted", page=1, limit=20,
        )

        assert total == 0

    @pytest.mark.asyncio
    async def test_get_event_registrations_event_not_found(self):
        from app.services.registration import RegistrationService

        db = AsyncMock()
        db.get.return_value = None

        with pytest.raises(NotFoundException, match="Event not found"):
            await RegistrationService.get_event_registrations(
                db, EVENT_ID, {"sub": str(TEACHER_ID), "role": "teacher"},
            )

    @pytest.mark.asyncio
    async def test_get_event_registrations_with_status_filter(self):
        from app.services.registration import RegistrationService

        db = AsyncMock()
        mock_event = MagicMock()
        mock_event.coordinator_id = uuid.UUID(str(TEACHER_ID))
        db.get.return_value = mock_event
        count_result = MagicMock()
        count_result.scalar_one.return_value = 0
        data_result = MagicMock()
        data_result.scalars.return_value = MagicMock(all=MagicMock(return_value=[]))
        db.execute = AsyncMock(side_effect=[count_result, data_result])

        registrations, total = await RegistrationService.get_event_registrations(
            db, EVENT_ID, {"sub": str(TEACHER_ID), "role": "teacher"},
            status_filter="accepted", page=1, limit=20,
        )
        assert total == 0

    @pytest.mark.asyncio
    async def test_accept_registration_event_not_found(self):
        from app.services.registration import RegistrationService

        db = AsyncMock()
        mock_reg = MagicMock()
        mock_reg.status = RegistrationStatus.PENDING
        mock_reg.event_id = EVENT_ID
        db.get.side_effect = [mock_reg, None]

        with pytest.raises(NotFoundException, match="Event not found"):
            await RegistrationService.accept_registration(
                db, REG_ID, {"sub": str(TEACHER_ID), "role": "teacher"},
            )

    @pytest.mark.asyncio
    async def test_reject_registration_event_not_found(self):
        from app.services.registration import RegistrationService

        db = AsyncMock()
        mock_reg = MagicMock()
        mock_reg.status = RegistrationStatus.PENDING
        mock_reg.event_id = EVENT_ID
        db.get.side_effect = [mock_reg, None]

        with pytest.raises(NotFoundException, match="Event not found"):
            await RegistrationService.reject_registration(
                db, REG_ID, {"sub": str(TEACHER_ID), "role": "teacher"},
            )

    @pytest.mark.asyncio
    async def test_reject_registration_not_pending(self):
        from app.services.registration import RegistrationService

        db = AsyncMock()
        mock_reg = MagicMock()
        mock_reg.status = RegistrationStatus.ACCEPTED
        mock_reg.event_id = EVENT_ID
        mock_event = MagicMock()
        mock_event.coordinator_id = uuid.UUID(str(TEACHER_ID))
        db.get.side_effect = [mock_reg, mock_event]

        with pytest.raises(ConflictException, match="not in pending status"):
            await RegistrationService.reject_registration(
                db, REG_ID, {"sub": str(TEACHER_ID), "role": "teacher"},
            )

@pytest.fixture
def student_app():
    from fastapi import FastAPI
    from app.api.v1.registrations import router
    from app.core.exceptions import register_exception_handlers

    app = FastAPI()
    app.include_router(router)
    register_exception_handlers(app)

    async def mock_user():
        return {"sub": str(STUDENT_ID), "role": "student"}

    app.dependency_overrides[deps.get_current_user] = mock_user
    return app


@pytest.fixture
def teacher_app():
    from fastapi import FastAPI
    from app.api.v1.registrations import router
    from app.core.exceptions import register_exception_handlers

    app = FastAPI()
    app.include_router(router)
    register_exception_handlers(app)

    async def mock_user():
        return {"sub": str(TEACHER_ID), "role": "teacher"}

    app.dependency_overrides[deps.get_current_user] = mock_user
    return app


class TestRegistrationsAPI:
    @pytest.mark.asyncio
    async def test_register_for_event_201(self, student_app):
        mock_reg = MagicMock()
        mock_reg.id = REG_ID
        mock_reg.event_id = EVENT_ID
        mock_reg.student_id = STUDENT_ID
        mock_reg.role_type = RegistrationRole.PARTICIPANT
        mock_reg.status = RegistrationStatus.PENDING
        mock_reg.registered_at = "2026-06-20T16:00:00Z"
        mock_reg.updated_at = "2026-06-20T16:00:00Z"

        with patch("app.services.registration.RegistrationService.register", return_value=mock_reg):
            transport = ASGITransport(app=student_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/registrations",
                    json={"event_id": str(EVENT_ID), "role_type": "participant"},
                )

        assert resp.status_code == 201
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["id"] == str(REG_ID)

    @pytest.mark.asyncio
    async def test_register_validation_error(self, student_app):
        transport = ASGITransport(app=student_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/registrations",
                json={},
            )

        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_register_conflict(self, student_app):
        with patch("app.services.registration.RegistrationService.register") as mock_reg:
            mock_reg.side_effect = ConflictException("Already registered for this event with this role")

            transport = ASGITransport(app=student_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/registrations",
                    json={"event_id": str(EVENT_ID), "role_type": "participant"},
                )

        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_get_my_registrations(self, student_app):
        mock_reg = MagicMock()
        mock_reg.id = REG_ID
        mock_reg.event_id = EVENT_ID
        mock_reg.role_type = RegistrationRole.PARTICIPANT
        mock_reg.status = RegistrationStatus.ACCEPTED
        mock_reg.registered_at = "2026-06-20T16:00:00Z"
        mock_reg.event = MagicMock()
        mock_reg.event.id = EVENT_ID
        mock_reg.event.title = "Tech Fest"
        mock_reg.event.event_type = "in_college"
        mock_reg.event.start_date = "2026-07-04T00:00:00Z"
        mock_reg.event.end_date = "2026-07-05T00:00:00Z"

        with patch("app.services.registration.RegistrationService.get_student_registrations", return_value=([mock_reg], 1)):
            transport = ASGITransport(app=student_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/registrations/my")

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert len(data["data"]) == 1
        assert data["meta"]["page"] == 1

    @pytest.mark.asyncio
    async def test_get_event_registrations_as_teacher(self, teacher_app):
        mock_reg = MagicMock()
        mock_reg.id = REG_ID
        mock_reg.event_id = EVENT_ID
        mock_reg.role_type = RegistrationRole.PARTICIPANT
        mock_reg.status = RegistrationStatus.ACCEPTED
        mock_reg.registered_at = "2026-06-20T16:00:00Z"
        mock_reg.student = MagicMock()
        mock_reg.student.id = STUDENT_ID
        mock_reg.student.name = "Priya Singh"
        mock_reg.student.email = "priya@college.edu"

        with patch("app.services.registration.RegistrationService.get_event_registrations", return_value=([mock_reg], 1)):
            transport = ASGITransport(app=teacher_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(f"/api/v1/registrations/event/{EVENT_ID}")

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert len(data["data"]) == 1

    @pytest.mark.asyncio
    async def test_accept_registration(self, teacher_app):
        mock_reg = MagicMock()
        mock_reg.id = REG_ID
        mock_reg.event_id = EVENT_ID
        mock_reg.student_id = STUDENT_ID
        mock_reg.role_type = RegistrationRole.PARTICIPANT
        mock_reg.status = RegistrationStatus.ACCEPTED
        mock_reg.registered_at = "2026-06-20T16:00:00Z"
        mock_reg.updated_at = "2026-06-20T17:00:00Z"

        with patch("app.services.registration.RegistrationService.accept_registration", return_value=mock_reg):
            transport = ASGITransport(app=teacher_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.patch(f"/api/v1/registrations/{REG_ID}/accept")

        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["status"] == "accepted"

    @pytest.mark.asyncio
    async def test_reject_registration(self, teacher_app):
        mock_reg = MagicMock()
        mock_reg.id = REG_ID
        mock_reg.event_id = EVENT_ID
        mock_reg.student_id = STUDENT_ID
        mock_reg.role_type = RegistrationRole.PARTICIPANT
        mock_reg.status = RegistrationStatus.REJECTED
        mock_reg.registered_at = "2026-06-20T16:00:00Z"
        mock_reg.updated_at = "2026-06-20T17:00:00Z"

        with patch("app.services.registration.RegistrationService.reject_registration", return_value=mock_reg):
            transport = ASGITransport(app=teacher_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.patch(f"/api/v1/registrations/{REG_ID}/reject")

        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["status"] == "rejected"

    @pytest.mark.asyncio
    async def test_registration_not_found(self, teacher_app):
        with patch("app.services.registration.RegistrationService.accept_registration") as mock_acc:
            mock_acc.side_effect = NotFoundException("Registration not found")

            transport = ASGITransport(app=teacher_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.patch(f"/api/v1/registrations/{uuid.uuid4()}/accept")

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_unauthorized_access(self):
        from fastapi import FastAPI
        from app.api.v1.registrations import router
        from app.core.exceptions import register_exception_handlers

        app = FastAPI()
        app.include_router(router)
        register_exception_handlers(app)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/registrations/my")
            assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_student_cannot_access_teacher_endpoints(self, student_app):
        transport = ASGITransport(app=student_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"/api/v1/registrations/event/{EVENT_ID}")
            assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_unknown_route(self, student_app):
        transport = ASGITransport(app=student_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/registrations/nonexistent")
        assert resp.status_code == 404
