import pytest
from datetime import datetime, timedelta
from pydantic import ValidationError


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
                resp = await client.get("/api/v1/events/999")

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

        app = FastAPI()
        app.include_router(router)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/events")
            assert resp.status_code == 401

            resp = await client.post("/api/v1/events", json={"title": "Test", "event_type": "in_college", "category": "both", "start_date": "2026-07-01T00:00:00", "end_date": "2026-07-02T00:00:00"})
            assert resp.status_code == 401
