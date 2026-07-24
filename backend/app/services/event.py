import uuid
from datetime import date
from typing import Optional
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.event import Event, EventStatus, EventType
from app.schemas.event import EventCreate
from app.services.notification import NotificationService, NotificationType, _render_notification


def _parse_enum(enum_cls, value: str, field: str):
    from app.core.exceptions import ValidationException

    try:
        return enum_cls(value)
    except ValueError:
        allowed = ", ".join(e.value for e in enum_cls)
        raise ValidationException(
            detail=f"Invalid {field} filter",
            errors=[{"loc": [field], "msg": f"must be one of: {allowed}"}],
        )


class EventService:

    @staticmethod
    async def list_events(
        db: AsyncSession,
        user: dict,
        page: int = 1,
        limit: int = 20,
        status: Optional[str] = None,
        event_type: Optional[str] = None,
        category: Optional[str] = None,
        search: Optional[str] = None,
    ) -> tuple[list[Event], int]:
        query = (
            select(Event)
            .options(
                selectinload(Event.creator),
                selectinload(Event.coordinator),
                selectinload(Event.registrations),
            )
        )

        user_role = user.get("role")
        user_id_str = user.get("sub")

        if user_role == "student":
            query = query.where(Event.status == EventStatus.APPROVED)
        elif user_role == "teacher":
            if user_id_str:
                try:
                    uid = uuid.UUID(user_id_str)
                    query = query.where(
                        or_(
                            Event.coordinator_id == uid,
                            Event.created_by == uid,
                        )
                    )
                except ValueError:
                    pass

        if status:
            query = query.where(Event.status == _parse_enum(EventStatus, status, "status"))
        if event_type:
            query = query.where(Event.event_type == _parse_enum(EventType, event_type, "type"))
        if category:
            from app.models.event import EventCategory
            query = query.where(Event.category == _parse_enum(EventCategory, category, "category"))
        if search:
            query = query.where(Event.title.ilike(f"%{search}%"))

        count_query = select(func.count()).select_from(query.subquery())
        total = await db.scalar(count_query) or 0

        query = query.order_by(Event.created_at.desc())
        query = query.offset((page - 1) * limit).limit(limit)

        result = await db.execute(query)
        events = list(result.scalars().all())
        return events, total

    @staticmethod
    async def create_event(
        db: AsyncSession,
        data: EventCreate,
        user: dict,
    ) -> Event:
        from app.core.exceptions import ValidationException, ForbiddenException

        today = date.today()
        if data.start_date.date() < today:
            raise ValidationException(
                detail="Start date must be today or a future date",
                errors=[{"loc": ["start_date"], "msg": "must be today or future"}],
            )
        if data.end_date < data.start_date:
            raise ValidationException(
                detail="End date must be after start date",
                errors=[{"loc": ["end_date"], "msg": "must be after start_date"}],
            )

        user_role = user.get("role")
        if data.event_type == "in_college" and user_role != "admin":
            raise ForbiddenException("Only admins can create in_college events")
        if data.event_type == "out_college" and user_role != "student":
            raise ForbiddenException("Only students can create out_college events")
        if data.event_type == "out_college" and data.category != "participant":
            raise ValidationException(
                detail="Out-of-college events only accept participation",
                errors=[{"loc": ["category"], "msg": "must be 'participant' for out_college events"}],
            )

        status = EventStatus.DRAFT if data.event_type == "in_college" else EventStatus.PENDING

        from app.models.event import EventCategory
        event = Event(
            title=data.title,
            description=data.description,
            event_type=EventType(data.event_type),
            category=EventCategory(data.category),
            venue=data.venue,
            status=status,
            start_date=data.start_date,
            end_date=data.end_date,
            max_registrations=data.max_registrations,
            created_by=uuid.UUID(user.get("sub")),
        )
        db.add(event)
        await db.commit()
        result = await db.execute(
            select(Event)
            .options(selectinload(Event.creator), selectinload(Event.coordinator))
            .where(Event.id == event.id)
        )
        return result.scalar_one()

    @staticmethod
    async def get_event_by_id(
        db: AsyncSession,
        event_id: str,
    ) -> Event:
        from app.core.exceptions import NotFoundException

        try:
            event_uuid = uuid.UUID(event_id)
        except ValueError:
            raise NotFoundException(detail="Event not found")

        query = (
            select(Event)
            .options(
                selectinload(Event.creator),
                selectinload(Event.coordinator),
            )
            .where(Event.id == event_uuid)
        )
        result = await db.execute(query)
        event = result.scalar_one_or_none()

        if not event:
            raise NotFoundException(detail="Event not found")

        return event

    @staticmethod
    async def update_event(
        db: AsyncSession,
        event_id: str,
        data: dict,
        user: dict,
    ) -> Event:
        from app.core.exceptions import ConflictException, ForbiddenException, ValidationException

        event = await EventService.get_event_by_id(db, event_id)

        user_id_str = user.get("sub")
        user_role = user.get("role")
        is_creator = user_id_str and uuid.UUID(user_id_str) == event.created_by
        is_admin = user_role == "admin"
        if not is_creator and not is_admin:
            raise ForbiddenException("Not authorized to update this event")

        status_val = event.status.value if hasattr(event.status, "value") else event.status
        if not is_admin and status_val not in (EventStatus.DRAFT.value, EventStatus.PENDING.value):
            raise ConflictException("Only draft or pending events can be updated")

        event_type = event.event_type.value if hasattr(event.event_type, "value") else event.event_type
        if data.get("category") and event_type == "out_college" and data["category"] != "participant":
            raise ValidationException(
                detail="Out-of-college events only accept participation",
                errors=[{"loc": ["category"], "msg": "must be 'participant' for out_college events"}],
            )

        for field, value in data.items():
            if value is not None:
                setattr(event, field, value)

        await db.commit()
        await db.refresh(event)
        return event

    @staticmethod
    async def approve_event(
        db: AsyncSession,
        event_id: str,
        admin_comment: Optional[str],
        user: dict,
    ) -> Event:
        from app.core.exceptions import ConflictException, ForbiddenException

        event = await EventService.get_event_by_id(db, event_id)

        if event.status == EventStatus.APPROVED:
            raise ConflictException("Event is already approved")
        if event.status == EventStatus.REJECTED:
            raise ConflictException("Cannot approve a rejected event")

        user_role = user.get("role")
        user_id_str = user.get("sub")
        is_admin = user_role == "admin"
        is_coordinator = user_id_str and event.coordinator_id and uuid.UUID(user_id_str) == event.coordinator_id

        if not is_admin and not is_coordinator:
            raise ForbiddenException("Not authorized to approve this event")
        if is_coordinator and user_role != "teacher":
            raise ForbiddenException("Only teachers can approve as coordinators")

        event.status = EventStatus.APPROVED
        title, message = _render_notification(
            NotificationType.EVENT_APPROVED,
            {"event_title": event.title},
        )
        await NotificationService.create_notification(
            db,
            user_id=event.created_by,
            notif_type=NotificationType.EVENT_APPROVED,
            title=title,
            message=message,
            entity_type="event",
            entity_id=event.id,
        )
        await db.commit()
        await db.refresh(event)
        return event

    @staticmethod
    async def reject_event(
        db: AsyncSession,
        event_id: str,
        admin_comment: str,
        user: dict,
    ) -> Event:
        from app.core.exceptions import ConflictException, ForbiddenException

        event = await EventService.get_event_by_id(db, event_id)

        if event.status == EventStatus.REJECTED:
            raise ConflictException("Event is already rejected")
        if event.status == EventStatus.APPROVED:
            raise ConflictException("Cannot reject an approved event")

        user_role = user.get("role")
        user_id_str = user.get("sub")
        is_admin = user_role == "admin"
        is_coordinator = user_id_str and event.coordinator_id and uuid.UUID(user_id_str) == event.coordinator_id

        if not is_admin and not is_coordinator:
            raise ForbiddenException("Not authorized to reject this event")

        event.status = EventStatus.REJECTED
        title, message = _render_notification(
            NotificationType.EVENT_REJECTED,
            {"event_title": event.title},
        )
        await NotificationService.create_notification(
            db,
            user_id=event.created_by,
            notif_type=NotificationType.EVENT_REJECTED,
            title=title,
            message=message,
            entity_type="event",
            entity_id=event.id,
        )
        await db.commit()
        await db.refresh(event)
        return event

    @staticmethod
    async def assign_coordinator(
        db: AsyncSession,
        event_id: str,
        coordinator_id: str,
    ) -> Event:
        from app.core.exceptions import NotFoundException, ValidationException
        from app.models.user import User

        event = await EventService.get_event_by_id(db, event_id)

        coord_query = select(User).where(User.id == uuid.UUID(coordinator_id))
        result = await db.execute(coord_query)
        coordinator = result.scalar_one_or_none()

        if not coordinator:
            raise NotFoundException(detail="Coordinator user not found")
        if coordinator.role.value != "teacher":
            raise ValidationException(
                detail="Coordinator must be a teacher",
                errors=[{"loc": ["coordinator_id"], "msg": "must be a teacher"}],
            )
        if coordinator.status.value != "active":
            raise ValidationException(
                detail="Coordinator must have active status",
                errors=[{"loc": ["coordinator_id"], "msg": "must be active"}],
            )

        event.coordinator_id = uuid.UUID(coordinator_id)
        await db.commit()
        await db.refresh(event)
        return event


