from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models.event import Event, EventStatus, EventType, EventCategory
from app.schemas.event import EventCreate

pytestmark = [pytest.mark.asyncio, pytest.mark.real_db]


class TestEventsRealDB:

    async def test_create_event_in_db(self, db_session, admin_user):
        from app.services.event import EventService

        future = datetime.now(timezone.utc) + timedelta(days=30)
        event = await EventService.create_event(
            db_session,
            EventCreate(
                title="Tech Fest",
                event_type="in_college",
                category="both",
                venue="Main Auditorium",
                start_date=future,
                end_date=future + timedelta(hours=4),
            ),
            {"sub": str(admin_user.id), "role": "admin"},
        )

        assert event.title == "Tech Fest"
        assert event.event_type == EventType.IN_COLLEGE
        assert event.status == EventStatus.DRAFT
        assert event.created_by == admin_user.id

        row = await db_session.execute(
            select(Event).where(Event.id == event.id)
        )
        db_event = row.scalar_one()
        assert db_event.title == "Tech Fest"
        assert db_event.venue == "Main Auditorium"

    async def test_list_events_paginated(self, db_session, admin_user):
        from app.services.event import EventService

        future = datetime.now(timezone.utc) + timedelta(days=30)
        for i in range(3):
            await EventService.create_event(
                db_session,
                EventCreate(
                    title=f"Event {i}",
                    event_type="in_college",
                    category="both",
                    venue="Auditorium",
                    start_date=future,
                    end_date=future + timedelta(hours=2),
                ),
                {"sub": str(admin_user.id), "role": "admin"},
            )

        events, total = await EventService.list_events(
            db_session, {"sub": str(admin_user.id), "role": "admin"},
            page=1, limit=10,
        )
        assert total == 3
        assert len(events) == 3

        events_p2, total_p2 = await EventService.list_events(
            db_session, {"sub": str(admin_user.id), "role": "admin"},
            page=1, limit=2,
        )
        assert total_p2 == 3
        assert len(events_p2) == 2

    async def test_get_event_by_id(self, db_session, admin_user):
        from app.services.event import EventService

        future = datetime.now(timezone.utc) + timedelta(days=30)
        created = await EventService.create_event(
            db_session,
            EventCreate(
                title="Find Me",
                event_type="in_college",
                category="both",
                venue="Auditorium",
                start_date=future,
                end_date=future + timedelta(hours=2),
            ),
            {"sub": str(admin_user.id), "role": "admin"},
        )

        fetched = await EventService.get_event_by_id(db_session, str(created.id))
        assert fetched.id == created.id
        assert fetched.title == "Find Me"

    async def test_get_event_not_found(self, db_session):
        from app.services.event import EventService
        from app.core.exceptions import NotFoundException

        with pytest.raises(NotFoundException):
            await EventService.get_event_by_id(
                db_session, "550e8400-e29b-41d4-a716-446655440000"
            )

    async def test_approve_event(self, db_session, admin_user):
        from app.services.event import EventService

        future = datetime.now(timezone.utc) + timedelta(days=30)
        event = await EventService.create_event(
            db_session,
            EventCreate(
                title="Approve Me",
                event_type="in_college",
                category="both",
                venue="Auditorium",
                start_date=future,
                end_date=future + timedelta(hours=2),
            ),
            {"sub": str(admin_user.id), "role": "admin"},
        )

        approved = await EventService.approve_event(
            db_session, str(event.id), None,
            {"sub": str(admin_user.id), "role": "admin"},
        )

        assert approved.status == EventStatus.APPROVED

        row = await db_session.execute(
            select(Event).where(Event.id == event.id)
        )
        db_event = row.scalar_one()
        assert db_event.status == EventStatus.APPROVED

    async def test_reject_event(self, db_session, admin_user):
        from app.services.event import EventService

        future = datetime.now(timezone.utc) + timedelta(days=30)
        event = await EventService.create_event(
            db_session,
            EventCreate(
                title="Reject Me",
                event_type="in_college",
                category="both",
                venue="Auditorium",
                start_date=future,
                end_date=future + timedelta(hours=2),
            ),
            {"sub": str(admin_user.id), "role": "admin"},
        )

        rejected = await EventService.reject_event(
            db_session, str(event.id), "Not suitable",
            {"sub": str(admin_user.id), "role": "admin"},
        )

        assert rejected.status == EventStatus.REJECTED

    async def test_assign_coordinator(self, db_session, admin_user, teacher_user):
        from app.services.event import EventService

        future = datetime.now(timezone.utc) + timedelta(days=30)
        event = await EventService.create_event(
            db_session,
            EventCreate(
                title="My Event",
                event_type="in_college",
                category="both",
                venue="Auditorium",
                start_date=future,
                end_date=future + timedelta(hours=2),
            ),
            {"sub": str(admin_user.id), "role": "admin"},
        )

        updated = await EventService.assign_coordinator(
            db_session, str(event.id), str(teacher_user.id),
            {"sub": str(admin_user.id), "role": "admin"},
        )

        assert updated.coordinator_id == teacher_user.id
