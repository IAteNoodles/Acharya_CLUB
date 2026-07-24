import uuid
import pytest
from datetime import datetime, timedelta, date
from pydantic import ValidationError
from unittest.mock import AsyncMock, MagicMock, patch


class TestEventSchemas:
    def test_event_create_valid(self):
        from app.schemas.event import EventCreate

        data = EventCreate(
            title="Tech Fest",
            event_type="in_college",
            category="both",
            venue="Main Auditorium",
            start_date=datetime.utcnow() + timedelta(days=1),
            end_date=datetime.utcnow() + timedelta(days=2),
        )
        assert data.title == "Tech Fest"
        assert data.event_type == "in_college"

    def test_event_create_rejects_empty_title(self):
        from app.schemas.event import EventCreate

        with pytest.raises(ValidationError):
            EventCreate(
                title="",
                event_type="in_college",
                category="both",
                venue="Main Auditorium",
                start_date=datetime.utcnow() + timedelta(days=1),
                end_date=datetime.utcnow() + timedelta(days=2),
            )

    def test_event_create_rejects_invalid_type(self):
        from app.schemas.event import EventCreate

        with pytest.raises(ValidationError):
            EventCreate(
                title="Fest",
                event_type="invalid",
                category="both",
                venue="Main Auditorium",
                start_date=datetime.utcnow() + timedelta(days=1),
                end_date=datetime.utcnow() + timedelta(days=2),
            )

    def test_event_create_accepts_max_registrations(self):
        from app.schemas.event import EventCreate

        data = EventCreate(
            title="Tech Fest",
            event_type="in_college",
            category="both",
            venue="Main Auditorium",
            start_date=datetime.utcnow() + timedelta(days=1),
            end_date=datetime.utcnow() + timedelta(days=2),
            max_registrations=50,
        )
        assert data.max_registrations == 50

    def test_event_create_defaults_max_registrations_to_zero(self):
        from app.schemas.event import EventCreate

        data = EventCreate(
            title="Tech Fest",
            event_type="in_college",
            category="both",
            venue="Main Auditorium",
            start_date=datetime.utcnow() + timedelta(days=1),
            end_date=datetime.utcnow() + timedelta(days=2),
        )
        assert data.max_registrations == 0

    def test_event_create_rejects_negative_max_registrations(self):
        from app.schemas.event import EventCreate

        with pytest.raises(ValidationError):
            EventCreate(
                title="Tech Fest",
                event_type="in_college",
                category="both",
                venue="Main Auditorium",
                start_date=datetime.utcnow() + timedelta(days=1),
                end_date=datetime.utcnow() + timedelta(days=2),
                max_registrations=-1,
            )

    def test_event_update_rejects_negative_max_registrations(self):
        from app.schemas.event import EventUpdate

        with pytest.raises(ValidationError):
            EventUpdate(max_registrations=-5)

    def test_event_create_rejects_invalid_category(self):
        from app.schemas.event import EventCreate

        with pytest.raises(ValidationError):
            EventCreate(
                title="Fest",
                event_type="in_college",
                category="spectator",
                venue="Main Auditorium",
                start_date=datetime.utcnow() + timedelta(days=1),
                end_date=datetime.utcnow() + timedelta(days=2),
            )

    def test_event_update_rejects_invalid_category(self):
        from app.schemas.event import EventUpdate

        with pytest.raises(ValidationError):
            EventUpdate(category="spectator")

    def test_event_update_accepts_valid_category(self):
        from app.schemas.event import EventUpdate

        assert EventUpdate(category="both").category == "both"

    def test_reject_schema_requires_comment(self):
        from app.schemas.event import EventReject

        with pytest.raises(ValidationError):
            EventReject()

    def test_assign_coordinator_validates_uuid(self):
        from app.schemas.event import EventAssignCoordinator

        with pytest.raises(ValidationError):
            EventAssignCoordinator(coordinator_id="not-a-uuid")


class TestEventService:
    @pytest.mark.asyncio
    async def test_list_events_paginated(self):
        from unittest.mock import AsyncMock, MagicMock
        from app.services.event import EventService

        db = AsyncMock()
        db.scalar.return_value = 0
        db.execute.return_value = MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[]))))

        events, total = await EventService.list_events(
            db, {"sub": "admin-uuid", "role": "admin"},
            page=1, limit=20,
        )

        assert total == 0
        assert events == []

    @pytest.mark.asyncio
    async def test_create_event_validates_dates(self):
        from unittest.mock import AsyncMock
        from app.services.event import EventService
        from app.schemas.event import EventCreate
        from app.core.exceptions import ValidationException

        db = AsyncMock()

        with pytest.raises(ValidationException):
            await EventService.create_event(
                db,
                EventCreate(
                    title="Test",
                    event_type="in_college",
                    category="both",
                    venue="Auditorium",
                    start_date=datetime.utcnow() - timedelta(days=10),
                    end_date=datetime.utcnow() - timedelta(days=5),
                ),
                {"sub": "admin-uuid", "role": "admin"},
            )

    @pytest.mark.asyncio
    async def test_get_event_not_found(self):
        from unittest.mock import AsyncMock, MagicMock
        from app.services.event import EventService
        from app.core.exceptions import NotFoundException

        db = AsyncMock()
        db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=None))

        with pytest.raises(NotFoundException):
            await EventService.get_event_by_id(db, "550e8400-e29b-41d4-a716-446655440000")


    @pytest.mark.asyncio
    async def test_list_events_student_sees_only_approved(self):
        from app.services.event import EventService

        db = AsyncMock()
        db.scalar.return_value = 0
        db.execute.return_value = MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[]))))

        events, total = await EventService.list_events(
            db, {"sub": str(uuid.uuid4()), "role": "student"},
            page=1, limit=20,
        )

        assert total == 0

    @pytest.mark.asyncio
    async def test_approve_event_not_authorized(self):
        from app.services.event import EventService
        from app.core.exceptions import ForbiddenException

        mock_event = MagicMock()
        mock_event.status = "pending"
        mock_event.coordinator_id = uuid.uuid4()

        db = AsyncMock()
        db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=mock_event))

        with pytest.raises(ForbiddenException, match="Not authorized to approve"):
            await EventService.approve_event(
                db, self.VALID_EVENT_ID, None,
                {"sub": str(uuid.uuid4()), "role": "teacher"},
            )

    @pytest.mark.asyncio
    async def test_reject_event_not_authorized(self):
        from app.services.event import EventService
        from app.core.exceptions import ForbiddenException

        mock_event = MagicMock()
        mock_event.status = "pending"
        mock_event.coordinator_id = uuid.uuid4()

        db = AsyncMock()
        db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=mock_event))

        with pytest.raises(ForbiddenException, match="Not authorized to reject"):
            await EventService.reject_event(
                db, self.VALID_EVENT_ID, "No",
                {"sub": str(uuid.uuid4()), "role": "teacher"},
            )

    @pytest.mark.asyncio
    async def test_assign_coordinator_success(self):
        from app.services.event import EventService

        mock_event = MagicMock()
        mock_coordinator = MagicMock()
        mock_coordinator.role = MagicMock(value="teacher")
        mock_coordinator.status = MagicMock(value="active")

        db = AsyncMock()
        db.execute.side_effect = [
            MagicMock(scalar_one_or_none=MagicMock(return_value=mock_event)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=mock_coordinator)),
        ]

        coordinator_id = str(uuid.uuid4())
        result = await EventService.assign_coordinator(db, self.VALID_EVENT_ID, coordinator_id)

        assert mock_event.coordinator_id == uuid.UUID(coordinator_id)
        db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_events_teacher_role_invalid_uuid(self):
        from app.services.event import EventService

        db = AsyncMock()
        db.scalar.return_value = 0
        db.execute.return_value = MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[]))))

        events, total = await EventService.list_events(
            db, {"sub": "not-a-uuid", "role": "teacher"},
            page=1, limit=20,
        )

        assert total == 0

    @pytest.mark.asyncio
    async def test_list_events_with_filters(self):
        from app.services.event import EventService

        db = AsyncMock()
        db.scalar.return_value = 5
        db.execute.return_value = MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[]))))

        events, total = await EventService.list_events(
            db, {"sub": "550e8400-e29b-41d4-a716-446655440000", "role": "teacher"},
            page=1, limit=20, status="approved", event_type="in_college",
            category="both", search="tech",
        )

        assert total == 5

    @pytest.mark.asyncio
    async def test_list_events_invalid_status_filter(self):
        from app.services.event import EventService
        from app.core.exceptions import ValidationException

        db = AsyncMock()

        with pytest.raises(ValidationException, match="Invalid status filter"):
            await EventService.list_events(
                db, {"sub": "admin-uuid", "role": "admin"},
                page=1, limit=20, status="bogus",
            )

    @pytest.mark.asyncio
    async def test_get_event_malformed_uuid_raises_not_found(self):
        from app.services.event import EventService
        from app.core.exceptions import NotFoundException

        with pytest.raises(NotFoundException):
            await EventService.get_event_by_id(AsyncMock(), "not-a-uuid")

    @pytest.mark.asyncio
    async def test_create_event_end_date_before_start(self):
        from app.services.event import EventService
        from app.schemas.event import EventCreate
        from app.core.exceptions import ValidationException

        with pytest.raises(ValidationException) as exc:
            await EventService.create_event(
                AsyncMock(),
                EventCreate(
                    title="Test", event_type="in_college", category="both",
                    venue="Hall", start_date=datetime.utcnow() + timedelta(days=5),
                    end_date=datetime.utcnow() + timedelta(days=3),
                ),
                {"sub": "admin-uuid", "role": "admin"},
            )
        assert "after" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_create_event_in_college_non_admin(self):
        from app.services.event import EventService
        from app.schemas.event import EventCreate
        from app.core.exceptions import ForbiddenException

        with pytest.raises(ForbiddenException, match="Only admins"):
            await EventService.create_event(
                AsyncMock(),
                EventCreate(
                    title="Test", event_type="in_college", category="both",
                    venue="Hall", start_date=datetime.utcnow() + timedelta(days=1),
                    end_date=datetime.utcnow() + timedelta(days=2),
                ),
                {"sub": str(uuid.uuid4()), "role": "teacher"},
            )

    @pytest.mark.asyncio
    async def test_create_event_out_college_non_student(self):
        from app.services.event import EventService
        from app.schemas.event import EventCreate
        from app.core.exceptions import ForbiddenException

        with pytest.raises(ForbiddenException, match="Only students"):
            await EventService.create_event(
                AsyncMock(),
                EventCreate(
                    title="Test", event_type="out_college", category="both",
                    venue="Hall", start_date=datetime.utcnow() + timedelta(days=1),
                    end_date=datetime.utcnow() + timedelta(days=2),
                ),
                {"sub": str(uuid.uuid4()), "role": "teacher"},
            )

    @pytest.mark.asyncio
    async def test_create_event_out_college_must_be_participant(self):
        from app.services.event import EventService
        from app.schemas.event import EventCreate
        from app.core.exceptions import ValidationException

        with pytest.raises(ValidationException, match="only accept participation"):
            await EventService.create_event(
                AsyncMock(),
                EventCreate(
                    title="Test", event_type="out_college", category="both",
                    venue="Hall", start_date=datetime.utcnow() + timedelta(days=1),
                    end_date=datetime.utcnow() + timedelta(days=2),
                ),
                {"sub": str(uuid.uuid4()), "role": "student"},
            )

    @pytest.mark.asyncio
    async def test_create_event_persists_max_registrations(self):
        from app.services.event import EventService
        from app.schemas.event import EventCreate

        db = AsyncMock()
        db.add = MagicMock()
        db.execute.return_value = MagicMock(scalar_one=MagicMock(return_value=MagicMock()))

        await EventService.create_event(
            db,
            EventCreate(
                title="Test", event_type="in_college", category="both",
                venue="Hall", start_date=datetime.utcnow() + timedelta(days=1),
                end_date=datetime.utcnow() + timedelta(days=2),
                max_registrations=25,
            ),
            {"sub": str(uuid.uuid4()), "role": "admin"},
        )

        created = db.add.call_args[0][0]
        assert created.max_registrations == 25

    VALID_EVENT_ID = "550e8400-e29b-41d4-a716-446655440000"

    @pytest.mark.asyncio
    async def test_update_event_not_authorized(self):
        from app.services.event import EventService
        from app.core.exceptions import ForbiddenException

        mock_event = MagicMock()
        mock_event.created_by = uuid.uuid4()
        mock_event.id = self.VALID_EVENT_ID

        db = AsyncMock()
        db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=mock_event))
        db.get.return_value = mock_event

        with pytest.raises(ForbiddenException, match="Not authorized"):
            await EventService.update_event(
                db, self.VALID_EVENT_ID, {"title": "Hacked"},
                {"sub": str(uuid.uuid4()), "role": "student"},
            )

    @pytest.mark.asyncio
    async def test_update_event_out_college_category_locked(self):
        from app.services.event import EventService
        from app.core.exceptions import ValidationException

        mock_event = MagicMock()
        mock_event.created_by = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        mock_event.event_type = "out_college"
        mock_event.status = "pending"

        db = AsyncMock()
        db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=mock_event))

        with pytest.raises(ValidationException, match="only accept participation"):
            await EventService.update_event(
                db, self.VALID_EVENT_ID, {"category": "both"},
                {"sub": "550e8400-e29b-41d4-a716-446655440000", "role": "student"},
            )

    @pytest.mark.asyncio
    async def test_update_event_success(self):
        from app.services.event import EventService

        mock_event = MagicMock()
        mock_event.created_by = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        mock_event.title = "Original"
        mock_event.event_type = "out_college"
        mock_event.status = "pending"

        db = AsyncMock()
        db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=mock_event))
        db.get.return_value = mock_event

        result = await EventService.update_event(
            db, self.VALID_EVENT_ID, {"title": "Updated"},
            {"sub": "550e8400-e29b-41d4-a716-446655440000", "role": "student"},
        )

        assert mock_event.title == "Updated"
        db.commit.assert_called_once()
        db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_event_creator_blocked_after_approval(self):
        from app.services.event import EventService
        from app.core.exceptions import ConflictException

        mock_event = MagicMock()
        mock_event.created_by = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        mock_event.status = "approved"

        db = AsyncMock()
        db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=mock_event))

        with pytest.raises(ConflictException, match="draft or pending"):
            await EventService.update_event(
                db, self.VALID_EVENT_ID, {"title": "Sneaky edit"},
                {"sub": "550e8400-e29b-41d4-a716-446655440000", "role": "student"},
            )

    @pytest.mark.asyncio
    async def test_update_event_admin_can_edit_approved(self):
        from app.services.event import EventService

        mock_event = MagicMock()
        mock_event.created_by = uuid.uuid4()
        mock_event.event_type = "in_college"
        mock_event.status = "approved"

        db = AsyncMock()
        db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=mock_event))

        await EventService.update_event(
            db, self.VALID_EVENT_ID, {"title": "Fixed typo"},
            {"sub": str(uuid.uuid4()), "role": "admin"},
        )

        assert mock_event.title == "Fixed typo"
        db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_approve_event_already_approved(self):
        from app.services.event import EventService
        from app.core.exceptions import ConflictException

        mock_event = MagicMock()
        mock_event.status = "approved"
        mock_event.id = self.VALID_EVENT_ID

        db = AsyncMock()
        db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=mock_event))
        db.get.return_value = mock_event

        with pytest.raises(ConflictException, match="already approved"):
            await EventService.approve_event(
                db, self.VALID_EVENT_ID, None,
                {"sub": "admin-uuid", "role": "admin"},
            )

    @pytest.mark.asyncio
    async def test_approve_event_already_rejected(self):
        from app.services.event import EventService
        from app.core.exceptions import ConflictException

        mock_event = MagicMock()
        mock_event.status = "rejected"
        mock_event.id = self.VALID_EVENT_ID

        db = AsyncMock()
        db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=mock_event))
        db.get.return_value = mock_event

        with pytest.raises(ConflictException, match="Cannot approve a rejected"):
            await EventService.approve_event(
                db, self.VALID_EVENT_ID, None,
                {"sub": "admin-uuid", "role": "admin"},
            )

    @pytest.mark.asyncio
    async def test_approve_event_coordinator_not_teacher(self):
        from app.services.event import EventService
        from app.core.exceptions import ForbiddenException

        mock_event = MagicMock()
        mock_event.status = "pending"
        mock_event.id = self.VALID_EVENT_ID
        mock_event.coordinator_id = uuid.UUID("550e8400-e29b-41d4-a716-446655440001")
        mock_event.title = "Test"
        mock_event.created_by = uuid.uuid4()

        db = AsyncMock()
        db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=mock_event))
        db.get.return_value = mock_event

        with pytest.raises(ForbiddenException, match="Only teachers"):
            await EventService.approve_event(
                db, self.VALID_EVENT_ID, None,
                {"sub": "550e8400-e29b-41d4-a716-446655440001", "role": "student"},
            )

    @pytest.mark.asyncio
    async def test_reject_event_already_rejected(self):
        from app.services.event import EventService
        from app.core.exceptions import ConflictException

        mock_event = MagicMock()
        mock_event.status = "rejected"
        mock_event.id = self.VALID_EVENT_ID

        db = AsyncMock()
        db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=mock_event))
        db.get.return_value = mock_event

        with pytest.raises(ConflictException, match="already rejected"):
            await EventService.reject_event(
                db, self.VALID_EVENT_ID, "Not suitable",
                {"sub": "admin-uuid", "role": "admin"},
            )

    @pytest.mark.asyncio
    async def test_reject_event_approved_blocked(self):
        from app.services.event import EventService
        from app.core.exceptions import ConflictException

        mock_event = MagicMock()
        mock_event.status = "approved"
        mock_event.id = self.VALID_EVENT_ID

        db = AsyncMock()
        db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=mock_event))

        with pytest.raises(ConflictException, match="Cannot reject an approved event"):
            await EventService.reject_event(
                db, self.VALID_EVENT_ID, "Changed my mind",
                {"sub": "admin-uuid", "role": "admin"},
            )

    @pytest.mark.asyncio
    async def test_assign_coordinator_user_not_found(self):
        from app.services.event import EventService
        from app.core.exceptions import NotFoundException

        mock_event = MagicMock()
        mock_event.id = self.VALID_EVENT_ID

        event_result = MagicMock(scalar_one_or_none=MagicMock(return_value=mock_event))
        none_result = MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        db = AsyncMock()
        db.execute.side_effect = [event_result, none_result]

        with pytest.raises(NotFoundException, match="Coordinator user not found"):
            await EventService.assign_coordinator(
                db, self.VALID_EVENT_ID, "550e8400-e29b-41d4-a716-446655440099",
            )

    @pytest.mark.asyncio
    async def test_assign_coordinator_not_teacher(self):
        from app.services.event import EventService
        from app.core.exceptions import ValidationException
        from app.models.user import User

        mock_event = MagicMock()
        mock_event.id = self.VALID_EVENT_ID

        mock_coord = MagicMock(spec=User)
        mock_coord.role.value = "student"
        mock_coord.status.value = "active"

        event_result = MagicMock(scalar_one_or_none=MagicMock(return_value=mock_event))
        coord_result = MagicMock(scalar_one_or_none=MagicMock(return_value=mock_coord))
        db = AsyncMock()
        db.execute.side_effect = [event_result, coord_result]

        with pytest.raises(ValidationException, match="must be a teacher"):
            await EventService.assign_coordinator(
                db, self.VALID_EVENT_ID, "550e8400-e29b-41d4-a716-446655440098",
            )

    @pytest.mark.asyncio
    async def test_assign_coordinator_not_active(self):
        from app.services.event import EventService
        from app.core.exceptions import ValidationException
        from app.models.user import User

        mock_event = MagicMock()
        mock_event.id = self.VALID_EVENT_ID

        mock_coord = MagicMock(spec=User)
        mock_coord.role.value = "teacher"
        mock_coord.status.value = "pending"

        event_result = MagicMock(scalar_one_or_none=MagicMock(return_value=mock_event))
        coord_result = MagicMock(scalar_one_or_none=MagicMock(return_value=mock_coord))
        db = AsyncMock()
        db.execute.side_effect = [event_result, coord_result]

        with pytest.raises(ValidationException, match="must have active status"):
            await EventService.assign_coordinator(
                db, self.VALID_EVENT_ID, "550e8400-e29b-41d4-a716-446655440097",
            )


class TestEventsAPI:
    @pytest.fixture
    def api_app(self):
        from fastapi import FastAPI
        from app.api.v1.events import router
        from app.api import deps
        from app.core.exceptions import register_exception_handlers

        app = FastAPI()
        app.include_router(router)
        register_exception_handlers(app)

        async def mock_admin():
            return {"sub": "admin-uuid", "role": "admin"}

        app.dependency_overrides[deps.get_current_user] = mock_admin
        return app

    @pytest.mark.asyncio
    async def test_list_events_returns_200(self, api_app):
        from httpx import ASGITransport, AsyncClient
        from unittest.mock import patch

        with patch("app.services.event.EventService.list_events") as mock_list:
            mock_list.return_value = ([], 0)

            transport = ASGITransport(app=api_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/events")

            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is True
            assert "items" in data
            assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_events_counts_accepted_and_exposes_coordinator(self, api_app):
        from httpx import ASGITransport, AsyncClient
        from unittest.mock import patch, MagicMock
        from app.models.event import EventType, EventCategory, EventStatus
        from app.models.registration import RegistrationStatus

        accepted = MagicMock()
        accepted.status = RegistrationStatus.ACCEPTED
        pending = MagicMock()
        pending.status = RegistrationStatus.PENDING

        mock_event = MagicMock()
        mock_event.id = "550e8400-e29b-41d4-a716-446655440000"
        mock_event.title = "Tech Fest"
        mock_event.event_type = EventType.IN_COLLEGE
        mock_event.category = EventCategory.BOTH
        mock_event.status = EventStatus.APPROVED
        mock_event.start_date = datetime.utcnow() + timedelta(days=1)
        mock_event.end_date = datetime.utcnow() + timedelta(days=2)
        mock_event.registrations = [accepted, pending]
        mock_event.creator = MagicMock()
        mock_event.creator.name = "Admin User"
        mock_event.coordinator = None

        with patch("app.services.event.EventService.list_events", return_value=([mock_event], 1)):
            transport = ASGITransport(app=api_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/events")

        assert resp.status_code == 200
        item = resp.json()["items"][0]
        assert item["registration_count"] == 1
        assert item["coordinator_name"] is None

    @pytest.mark.asyncio
    async def test_list_events_with_search(self, api_app):
        from httpx import ASGITransport, AsyncClient
        from unittest.mock import patch

        with patch("app.services.event.EventService.list_events") as mock_list:
            mock_list.return_value = ([], 0)

            transport = ASGITransport(app=api_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/events?search=tech&type=in_college")

            assert resp.status_code == 200
            assert mock_list.call_args[1]["search"] == "tech"
            assert mock_list.call_args[1]["event_type"] == "in_college"

    @pytest.mark.asyncio
    async def test_create_event_201(self, api_app):
        from httpx import ASGITransport, AsyncClient
        from unittest.mock import patch, MagicMock
        from app.models.event import Event, EventType, EventCategory, EventStatus

        mock_event = MagicMock(spec=Event)
        mock_event.id = "550e8400-e29b-41d4-a716-446655440000"
        mock_event.title = "Tech Fest"
        mock_event.event_type = EventType.IN_COLLEGE
        mock_event.category = EventCategory.BOTH
        mock_event.status = EventStatus.DRAFT
        mock_event.description = None
        mock_event.venue = ""
        mock_event.start_date = datetime.utcnow() + timedelta(days=1)
        mock_event.end_date = datetime.utcnow() + timedelta(days=2)
        mock_event.max_registrations = 0
        mock_event.creator = None
        mock_event.coordinator = None
        mock_event.created_at = datetime.utcnow()
        mock_event.updated_at = datetime.utcnow()

        with patch("app.services.event.EventService.create_event", return_value=mock_event):
            transport = ASGITransport(app=api_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post("/api/v1/events", json={
                    "title": "Tech Fest",
                    "event_type": "in_college",
                    "category": "both",
                    "venue": "Main Auditorium",
                    "start_date": (datetime.utcnow() + timedelta(days=1)).isoformat(),
                    "end_date": (datetime.utcnow() + timedelta(days=2)).isoformat(),
                })

            assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_get_event_malformed_uuid_returns_422_envelope(self, api_app):
        from httpx import ASGITransport, AsyncClient

        transport = ASGITransport(app=api_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/events/not-a-uuid")

        assert resp.status_code == 422
        data = resp.json()
        assert data["success"] is False
        assert data["error"]["code"] == "VALIDATION_ERROR"

    @pytest.mark.asyncio
    async def test_list_events_invalid_status_returns_422(self, api_app):
        from httpx import ASGITransport, AsyncClient

        transport = ASGITransport(app=api_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/events?status=bogus")

        assert resp.status_code == 422
        data = resp.json()
        assert data["success"] is False
        assert data["error"]["code"] == "VALIDATION_ERROR"

    @pytest.mark.asyncio
    async def test_create_event_invalid_body(self, api_app):
        from httpx import ASGITransport, AsyncClient

        transport = ASGITransport(app=api_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/v1/events", json={"title": ""})

        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_get_event_by_id(self, api_app):
        from httpx import ASGITransport, AsyncClient
        from unittest.mock import patch, MagicMock
        from app.models.event import Event, EventType, EventCategory, EventStatus

        mock_event = MagicMock(spec=Event)
        mock_event.id = "550e8400-e29b-41d4-a716-446655440000"
        mock_event.title = "Event 1"
        mock_event.event_type = EventType.IN_COLLEGE
        mock_event.category = EventCategory.BOTH
        mock_event.status = EventStatus.APPROVED
        mock_event.description = None
        mock_event.venue = ""
        mock_event.start_date = datetime.utcnow()
        mock_event.end_date = datetime.utcnow()
        mock_event.max_registrations = 0
        mock_event.creator = None
        mock_event.coordinator = None
        mock_event.created_at = datetime.utcnow()
        mock_event.updated_at = datetime.utcnow()

        with patch("app.services.event.EventService.get_event_by_id", return_value=mock_event):
            transport = ASGITransport(app=api_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/events/550e8400-e29b-41d4-a716-446655440000")

            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is True
            assert data["title"] == "Event 1"

    @pytest.mark.asyncio
    async def test_get_event_not_found(self, api_app):
        from httpx import ASGITransport, AsyncClient
        from unittest.mock import patch
        from app.core.exceptions import NotFoundException

        with patch("app.services.event.EventService.get_event_by_id") as mock_get:
            mock_get.side_effect = NotFoundException(detail="Event not found")

            transport = ASGITransport(app=api_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(f"/api/v1/events/{uuid.uuid4()}")

            assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_event(self, api_app):
        from httpx import ASGITransport, AsyncClient
        from unittest.mock import patch, MagicMock
        from app.models.event import Event, EventType, EventCategory, EventStatus

        mock_event = MagicMock(spec=Event)
        mock_event.id = "550e8400-e29b-41d4-a716-446655440000"
        mock_event.title = "Updated Title"
        mock_event.event_type = EventType.IN_COLLEGE
        mock_event.category = EventCategory.BOTH
        mock_event.status = EventStatus.DRAFT
        mock_event.description = None
        mock_event.venue = ""
        mock_event.start_date = datetime.utcnow()
        mock_event.end_date = datetime.utcnow()
        mock_event.max_registrations = 0
        mock_event.creator = None
        mock_event.coordinator = None
        mock_event.created_at = datetime.utcnow()
        mock_event.updated_at = datetime.utcnow()

        with patch("app.services.event.EventService.update_event", return_value=mock_event):
            transport = ASGITransport(app=api_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.patch("/api/v1/events/550e8400-e29b-41d4-a716-446655440000", json={"title": "Updated Title"})

            assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_approve_event(self, api_app):
        from httpx import ASGITransport, AsyncClient
        from unittest.mock import patch, MagicMock
        from app.models.event import Event, EventType, EventCategory, EventStatus

        mock_event = MagicMock(spec=Event)
        mock_event.id = "550e8400-e29b-41d4-a716-446655440000"
        mock_event.title = "Event"
        mock_event.event_type = EventType.OUT_COLLEGE
        mock_event.category = EventCategory.BOTH
        mock_event.status = EventStatus.APPROVED
        mock_event.description = None
        mock_event.venue = ""
        mock_event.start_date = datetime.utcnow()
        mock_event.end_date = datetime.utcnow()
        mock_event.max_registrations = 0
        mock_event.creator = None
        mock_event.coordinator = None
        mock_event.created_at = datetime.utcnow()
        mock_event.updated_at = datetime.utcnow()

        with patch("app.services.event.EventService.approve_event", return_value=mock_event):
            transport = ASGITransport(app=api_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.patch("/api/v1/events/550e8400-e29b-41d4-a716-446655440000/approve", json={})

            assert resp.status_code == 200
            assert resp.json()["status"] == "approved"

    @pytest.mark.asyncio
    async def test_reject_event(self, api_app):
        from httpx import ASGITransport, AsyncClient
        from unittest.mock import patch, MagicMock
        from app.models.event import Event, EventType, EventCategory, EventStatus

        mock_event = MagicMock(spec=Event)
        mock_event.id = "550e8400-e29b-41d4-a716-446655440000"
        mock_event.title = "Event"
        mock_event.event_type = EventType.OUT_COLLEGE
        mock_event.category = EventCategory.BOTH
        mock_event.status = EventStatus.REJECTED
        mock_event.description = None
        mock_event.venue = ""
        mock_event.start_date = datetime.utcnow()
        mock_event.end_date = datetime.utcnow()
        mock_event.max_registrations = 0
        mock_event.creator = None
        mock_event.coordinator = None
        mock_event.created_at = datetime.utcnow()
        mock_event.updated_at = datetime.utcnow()

        with patch("app.services.event.EventService.reject_event", return_value=mock_event):
            transport = ASGITransport(app=api_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.patch("/api/v1/events/550e8400-e29b-41d4-a716-446655440000/reject", json={"admin_comment": "Not suitable"})

            assert resp.status_code == 200
            assert resp.json()["status"] == "rejected"

    @pytest.mark.asyncio
    async def test_reject_event_missing_comment(self, api_app):
        from httpx import ASGITransport, AsyncClient

        transport = ASGITransport(app=api_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.patch("/api/v1/events/550e8400-e29b-41d4-a716-446655440000/reject", json={})

        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_assign_coordinator(self, api_app):
        from httpx import ASGITransport, AsyncClient
        from unittest.mock import patch, MagicMock
        from app.models.event import Event, EventType, EventCategory, EventStatus

        mock_event = MagicMock(spec=Event)
        mock_event.id = "550e8400-e29b-41d4-a716-446655440000"
        mock_event.title = "Event"
        mock_event.event_type = EventType.OUT_COLLEGE
        mock_event.category = EventCategory.BOTH
        mock_event.status = EventStatus.PENDING
        mock_event.description = None
        mock_event.venue = ""
        mock_event.start_date = datetime.utcnow()
        mock_event.end_date = datetime.utcnow()
        mock_event.max_registrations = 0
        mock_event.creator = None
        mock_event.coordinator = None
        mock_event.coordinator_id = None
        mock_event.created_at = datetime.utcnow()
        mock_event.updated_at = datetime.utcnow()

        with patch("app.services.event.EventService.assign_coordinator", return_value=mock_event):
            transport = ASGITransport(app=api_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.patch(
                    "/api/v1/events/550e8400-e29b-41d4-a716-446655440000/assign-coordinator",
                    json={"coordinator_id": "550e8400-e29b-41d4-a716-446655440001"},
                )

            assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_events_require_auth(self):
        from httpx import ASGITransport, AsyncClient
        from fastapi import FastAPI
        from app.api.v1.events import router
        from app.core.exceptions import register_exception_handlers

        app = FastAPI()
        app.include_router(router)
        register_exception_handlers(app)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/events")
            assert resp.status_code == 401

            resp = await client.post("/api/v1/events", json={"title": "Test", "event_type": "in_college", "category": "both", "start_date": "2026-07-01T00:00:00", "end_date": "2026-07-02T00:00:00"})
            assert resp.status_code == 401
