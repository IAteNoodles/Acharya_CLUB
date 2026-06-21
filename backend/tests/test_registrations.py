import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError
from httpx import ASGITransport, AsyncClient

from app.api import deps
from app.core.exceptions import ConflictException, ForbiddenException, NotFoundException
from app.models.event import EventType
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

    def test_proof_upload_request_valid(self):
        from app.schemas.registration import ProofUploadRequest

        data = ProofUploadRequest(file_name="proof.pdf", file_type="application/pdf")
        assert data.file_name == "proof.pdf"

    def test_proof_upload_request_rejects_invalid_type(self):
        from app.schemas.registration import ProofUploadRequest

        with pytest.raises(ValidationError):
            ProofUploadRequest(file_name="bad.exe", file_type="application/x-msdownload")

    def test_proof_upload_request_rejects_empty_name(self):
        from app.schemas.registration import ProofUploadRequest

        with pytest.raises(ValidationError):
            ProofUploadRequest(file_name="", file_type="image/jpeg")


class TestRegistrationService:
    @pytest.mark.asyncio
    async def test_register_success(self):
        from app.services.registration import RegistrationService

        db = AsyncMock()
        mock_event = MagicMock()
        mock_event.status = "approved"
        mock_event.coordinator_id = uuid.uuid4()
        db.get.return_value = mock_event
        db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=None))

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
        db.get.return_value = mock_event
        db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=MagicMock()))

        with pytest.raises(ConflictException, match="Already registered"):
            await RegistrationService.register(
                db, EVENT_ID, "participant",
                {"sub": str(STUDENT_ID), "role": "student"},
            )

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
        db.get.side_effect = [mock_reg, mock_event]

        reg = await RegistrationService.accept_registration(
            db, REG_ID, {"sub": str(TEACHER_ID), "role": "teacher"},
        )

        assert reg.status == RegistrationStatus.ACCEPTED
        assert db.commit.call_count == 2
        assert db.refresh.call_count == 2

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
    async def test_request_proof_url_success(self):
        from app.services.registration import RegistrationService

        db = AsyncMock()
        mock_reg = MagicMock()
        mock_reg.student_id = STUDENT_ID
        mock_reg.event_id = EVENT_ID
        mock_reg.status = RegistrationStatus.ACCEPTED
        mock_event = MagicMock()
        mock_event.event_type = EventType.OUT_COLLEGE
        db.get.side_effect = [mock_reg, mock_event]

        result = await RegistrationService.request_proof_url(
            db, REG_ID, {"sub": str(STUDENT_ID), "role": "student"}, "proof.pdf",
        )

        assert "upload_url" in result
        assert "file_key" in result
        assert result["expires_in"] == 300

    @pytest.mark.asyncio
    async def test_request_proof_url_not_owner(self):
        from app.services.registration import RegistrationService

        db = AsyncMock()
        mock_reg = MagicMock()
        mock_reg.student_id = uuid.uuid4()
        db.get.return_value = mock_reg

        with pytest.raises(ForbiddenException):
            await RegistrationService.request_proof_url(
                db, REG_ID, {"sub": str(STUDENT_ID), "role": "student"}, "proof.pdf",
            )

    @pytest.mark.asyncio
    async def test_request_proof_url_in_college(self):
        from app.services.registration import RegistrationService

        db = AsyncMock()
        mock_reg = MagicMock()
        mock_reg.student_id = STUDENT_ID
        mock_reg.event_id = EVENT_ID
        mock_reg.status = RegistrationStatus.ACCEPTED
        mock_event = MagicMock()
        mock_event.event_type = EventType.IN_COLLEGE
        db.get.side_effect = [mock_reg, mock_event]

        with pytest.raises(ConflictException, match="only for out-college"):
            await RegistrationService.request_proof_url(
                db, REG_ID, {"sub": str(STUDENT_ID), "role": "student"}, "proof.pdf",
            )

    @pytest.mark.asyncio
    async def test_request_proof_url_not_accepted(self):
        from app.services.registration import RegistrationService

        db = AsyncMock()
        mock_reg = MagicMock()
        mock_reg.student_id = STUDENT_ID
        mock_reg.event_id = EVENT_ID
        mock_reg.status = RegistrationStatus.PENDING
        mock_event = MagicMock()
        mock_event.event_type = EventType.OUT_COLLEGE
        db.get.side_effect = [mock_reg, mock_event]

        with pytest.raises(ConflictException, match="must be accepted"):
            await RegistrationService.request_proof_url(
                db, REG_ID, {"sub": str(STUDENT_ID), "role": "student"}, "proof.pdf",
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
    async def test_request_proof_upload(self, student_app):
        with patch("app.services.registration.RegistrationService.request_proof_url", return_value={
            "upload_url": "https://mock-s3.example.com/proofs/file.pdf",
            "file_key": "proofs/file.pdf",
            "expires_in": 300,
        }):
            transport = ASGITransport(app=student_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    f"/api/v1/registrations/{REG_ID}/proof",
                    json={"file_name": "id-card.pdf", "file_type": "application/pdf"},
                )

        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["upload_url"] is not None

    @pytest.mark.asyncio
    async def test_proof_upload_validation_error(self, student_app):
        transport = ASGITransport(app=student_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                f"/api/v1/registrations/{REG_ID}/proof",
                json={"file_name": "test.exe", "file_type": "application/x-msdownload"},
            )

        assert resp.status_code == 422

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

        app = FastAPI()
        app.include_router(router)

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
