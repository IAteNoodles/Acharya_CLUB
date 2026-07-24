import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.api.deps import get_current_user
from app.core.database import get_db
from app.schemas.event import (
    EventCreate,
    EventUpdate,
    EventApprove,
    EventReject,
    EventAssignCoordinator,
    EventOut,
    EventListItem,
    PaginatedResponse,
)
from app.services.event import EventService

router = APIRouter(prefix="/api/v1/events", tags=["events"])


@router.get("", response_model=PaginatedResponse)
async def list_events(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None, alias="type"),
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    events, total = await EventService.list_events(
        db, current_user,
        page=page, limit=limit,
        status=status, event_type=event_type,
        category=category, search=search,
    )
    items = [
        EventListItem(
            id=str(e.id),
            title=e.title,
            event_type=e.event_type.value,
            category=e.category.value,
            status=e.status.value,
            start_date=e.start_date,
            end_date=e.end_date,
            registration_count=sum(
                1 for r in (getattr(e, "registrations", []) or []) if r.status == "accepted"
            ),
            created_by_name=e.creator.name if e.creator else None,
            coordinator_name=e.coordinator.name if e.coordinator else None,
        )
        for e in events
    ]
    total_pages = max(1, (total + limit - 1) // limit) if total else 0
    return PaginatedResponse(
        items=[i.model_dump() for i in items],
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages,
    )


@router.post("", response_model=EventOut, status_code=201)
async def create_event(
    data: EventCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    event = await EventService.create_event(db, data, current_user)
    return _event_to_out(event)


@router.get("/{event_id}", response_model=EventOut)
async def get_event(
    event_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    event = await EventService.get_event_by_id(db, str(event_id))
    return _event_to_out(event)


@router.patch("/{event_id}", response_model=EventOut)
async def update_event(
    event_id: uuid.UUID,
    data: EventUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    event = await EventService.update_event(
        db, str(event_id), data.model_dump(exclude_unset=True), current_user,
    )
    return _event_to_out(event)


@router.patch("/{event_id}/approve", response_model=EventOut)
async def approve_event(
    event_id: uuid.UUID,
    data: EventApprove,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    event = await EventService.approve_event(db, str(event_id), data.admin_comment, current_user)
    return _event_to_out(event)


@router.patch("/{event_id}/reject", response_model=EventOut)
async def reject_event(
    event_id: uuid.UUID,
    data: EventReject,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    event = await EventService.reject_event(db, str(event_id), data.admin_comment, current_user)
    return _event_to_out(event)


@router.patch("/{event_id}/assign-coordinator", response_model=EventOut)
async def assign_coordinator(
    event_id: uuid.UUID,
    data: EventAssignCoordinator,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    event = await EventService.assign_coordinator(db, str(event_id), data.coordinator_id)
    return _event_to_out(event)


def _event_to_out(event) -> EventOut:
    return EventOut(
        id=str(event.id),
        title=event.title,
        description=event.description,
        event_type=event.event_type.value if hasattr(event.event_type, "value") else event.event_type,
        category=event.category.value if hasattr(event.category, "value") else event.category,
        status=event.status.value if hasattr(event.status, "value") else event.status,
        venue=event.venue,
        start_date=event.start_date,
        end_date=event.end_date,
        max_registrations=event.max_registrations,
        created_by={
            "id": str(event.creator.id),
            "name": event.creator.name,
            "email": event.creator.email,
        } if event.creator else None,
        coordinator={
            "id": str(event.coordinator.id),
            "name": event.coordinator.name,
            "email": event.coordinator.email,
        } if event.coordinator else None,
        created_at=event.created_at,
        updated_at=event.updated_at,
    )
