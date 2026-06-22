from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models.event import Event, EventStatus, EventType, EventCategory
from app.models.registration import Registration, RegistrationRole, RegistrationStatus
from app.models.user import User, Role, UserStatus

pytestmark = pytest.mark.asyncio


async def _approved_event(db, admin_user, teacher_user):
    future = datetime.now(timezone.utc) + timedelta(days=30)
    event = Event(
        title="Reg Test Event",
        event_type=EventType.IN_COLLEGE,
        category=EventCategory.BOTH,
        status=EventStatus.APPROVED,
        venue="Auditorium",
        start_date=future,
        end_date=future + timedelta(hours=2),
        created_by=admin_user.id,
        coordinator_id=teacher_user.id,
    )
    db.add(event)
    await db.flush()
    return event


class TestRegistrationsRealDB:

    async def test_register_creates_record(self, db_session, admin_user, teacher_user):
        from app.services.registration import RegistrationService

        event = await _approved_event(db_session, admin_user, teacher_user)
        student_id = admin_user.id

        reg = await RegistrationService.register(
            db_session, event.id, "participant",
            {"sub": str(student_id), "role": "student"},
        )

        assert reg.event_id == event.id
        assert reg.student_id == student_id
        assert reg.role_type == RegistrationRole.PARTICIPANT
        assert reg.status == RegistrationStatus.PENDING

        row = await db_session.execute(
            select(Registration).where(Registration.id == reg.id)
        )
        db_reg = row.scalar_one()
        assert db_reg.student_id == student_id

    async def test_register_duplicate_raises(self, db_session, admin_user, teacher_user):
        from app.services.registration import RegistrationService

        event = await _approved_event(db_session, admin_user, teacher_user)
        student_id = admin_user.id

        await RegistrationService.register(
            db_session, event.id, "participant",
            {"sub": str(student_id), "role": "student"},
        )

        with pytest.raises(Exception) as exc:
            await RegistrationService.register(
                db_session, event.id, "participant",
                {"sub": str(student_id), "role": "student"},
            )
        assert "Already registered" in str(exc.value)

    async def test_register_event_not_approved(self, db_session, admin_user, teacher_user):
        from app.services.registration import RegistrationService

        future = datetime.now(timezone.utc) + timedelta(days=30)
        event = Event(
            title="Draft Event",
            event_type=EventType.IN_COLLEGE,
            category=EventCategory.BOTH,
            status=EventStatus.DRAFT,
            venue="Auditorium",
            start_date=future,
            end_date=future + timedelta(hours=2),
            created_by=admin_user.id,
            coordinator_id=teacher_user.id,
        )
        db_session.add(event)
        await db_session.flush()

        with pytest.raises(Exception) as exc:
            await RegistrationService.register(
                db_session, event.id, "participant",
                {"sub": str(admin_user.id), "role": "student"},
            )
        assert "not open" in str(exc.value).lower()

    async def test_accept_registration(self, db_session, admin_user, teacher_user):
        from app.services.registration import RegistrationService

        event = await _approved_event(db_session, admin_user, teacher_user)
        reg = await RegistrationService.register(
            db_session, event.id, "participant",
            {"sub": str(admin_user.id), "role": "student"},
        )

        accepted = await RegistrationService.accept_registration(
            db_session, reg.id,
            {"sub": str(teacher_user.id), "role": "teacher"},
        )

        assert accepted.status == RegistrationStatus.ACCEPTED

    async def test_reject_registration(self, db_session, admin_user, teacher_user):
        from app.services.registration import RegistrationService

        event = await _approved_event(db_session, admin_user, teacher_user)
        reg = await RegistrationService.register(
            db_session, event.id, "participant",
            {"sub": str(admin_user.id), "role": "student"},
        )

        rejected = await RegistrationService.reject_registration(
            db_session, reg.id,
            {"sub": str(teacher_user.id), "role": "teacher"},
        )

        assert rejected.status == RegistrationStatus.REJECTED
