import uuid
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException, ForbiddenException, ConflictException
from app.models.event import Event, EventStatus
from app.models.registration import Registration, RegistrationStatus
from app.services.notification import NotificationService, NotificationType, _render_notification


class RegistrationService:

    @staticmethod
    async def register(
        db: AsyncSession,
        event_id: uuid.UUID,
        role_type: str,
        current_user: dict,
    ) -> Registration:
        event = await db.get(Event, event_id)
        if not event:
            raise NotFoundException("Event not found")
        if event.status != EventStatus.APPROVED:
            raise ConflictException("Event is not open for registration")
        if not event.coordinator_id:
            raise ConflictException("Event has no coordinator assigned")

        if event.max_registrations > 0:
            count_result = await db.execute(
                select(func.count()).select_from(Registration).where(
                    Registration.event_id == event_id,
                    Registration.status == RegistrationStatus.ACCEPTED,
                )
            )
            accepted_count = count_result.scalar_one()
            if accepted_count >= event.max_registrations:
                raise ConflictException("Event has reached its maximum registration capacity")

        result = await db.execute(
            select(Registration).where(
                Registration.event_id == event_id,
                Registration.student_id == uuid.UUID(current_user["sub"]),
                Registration.role_type == role_type,
            )
        )
        if result.scalar_one_or_none():
            raise ConflictException("Already registered for this event with this role")

        reg = Registration(
            event_id=event_id,
            student_id=uuid.UUID(current_user["sub"]),
            role_type=role_type,
        )
        db.add(reg)
        await db.commit()
        await db.refresh(reg)
        return reg

    @staticmethod
    async def get_student_registrations(
        db: AsyncSession,
        student_id: str,
        status_filter: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[Registration], int]:
        stmt = select(Registration).where(Registration.student_id == student_id)
        count_stmt = select(func.count()).select_from(Registration).where(Registration.student_id == student_id)

        if status_filter:
            stmt = stmt.where(Registration.status == status_filter)
            count_stmt = count_stmt.where(Registration.status == status_filter)

        stmt = (
            stmt
            .order_by(Registration.registered_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )

        total_result = await db.execute(count_stmt)
        total = total_result.scalar_one()

        result = await db.execute(stmt)
        registrations = list(result.scalars().all())

        return registrations, total

    @staticmethod
    async def get_event_registrations(
        db: AsyncSession,
        event_id: uuid.UUID,
        current_user: dict,
        status_filter: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[Registration], int]:
        event = await db.get(Event, event_id)
        if not event:
            raise NotFoundException("Event not found")

        user_id = uuid.UUID(current_user["sub"])
        if current_user["role"] != "admin" and event.coordinator_id != user_id:
            raise ForbiddenException("You are not the coordinator of this event")

        stmt = select(Registration).where(Registration.event_id == event_id)
        count_stmt = select(func.count()).select_from(Registration).where(Registration.event_id == event_id)

        if status_filter:
            stmt = stmt.where(Registration.status == status_filter)
            count_stmt = count_stmt.where(Registration.status == status_filter)

        stmt = (
            stmt
            .order_by(Registration.registered_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )

        total_result = await db.execute(count_stmt)
        total = total_result.scalar_one()

        result = await db.execute(stmt)
        registrations = list(result.scalars().all())

        return registrations, total

    @staticmethod
    async def accept_registration(
        db: AsyncSession,
        registration_id: uuid.UUID,
        current_user: dict,
    ) -> Registration:
        reg = await db.get(Registration, registration_id)
        if not reg:
            raise NotFoundException("Registration not found")

        event = await db.get(Event, reg.event_id)
        if not event:
            raise NotFoundException("Event not found")

        user_id = uuid.UUID(current_user["sub"])
        if current_user["role"] != "admin" and event.coordinator_id != user_id:
            raise ForbiddenException("You are not the coordinator of this event")

        if reg.status != RegistrationStatus.PENDING:
            raise ConflictException("Registration is not in pending status")

        reg.status = RegistrationStatus.ACCEPTED
        title, message = _render_notification(
            NotificationType.REGISTRATION_ACCEPTED,
            {"event_title": event.title, "role": reg.role_type.value if hasattr(reg.role_type, "value") else reg.role_type},
        )
        await NotificationService.create_notification(
            db,
            user_id=reg.student_id,
            notif_type=NotificationType.REGISTRATION_ACCEPTED,
            title=title,
            message=message,
            entity_type="registration",
            entity_id=reg.id,
        )
        await db.commit()
        await db.refresh(reg)
        return reg

    @staticmethod
    async def reject_registration(
        db: AsyncSession,
        registration_id: uuid.UUID,
        current_user: dict,
    ) -> Registration:
        reg = await db.get(Registration, registration_id)
        if not reg:
            raise NotFoundException("Registration not found")

        event = await db.get(Event, reg.event_id)
        if not event:
            raise NotFoundException("Event not found")

        user_id = uuid.UUID(current_user["sub"])
        if current_user["role"] != "admin" and event.coordinator_id != user_id:
            raise ForbiddenException("You are not the coordinator of this event")

        if reg.status != RegistrationStatus.PENDING:
            raise ConflictException("Registration is not in pending status")

        reg.status = RegistrationStatus.REJECTED
        title, message = _render_notification(
            NotificationType.REGISTRATION_REJECTED,
            {"event_title": event.title, "role": reg.role_type.value if hasattr(reg.role_type, "value") else reg.role_type},
        )
        await NotificationService.create_notification(
            db,
            user_id=reg.student_id,
            notif_type=NotificationType.REGISTRATION_REJECTED,
            title=title,
            message=message,
            entity_type="registration",
            entity_id=reg.id,
        )
        await db.commit()
        await db.refresh(reg)
        return reg


