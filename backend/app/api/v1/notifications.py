import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user
from app.core.database import get_db
from app.schemas.common import SuccessResponse, PaginatedResponse, PaginatedMeta
from app.schemas.notification import NotificationOut, UnreadCountResponse, MarkReadAllResponse
from app.services.notification import NotificationService

router = APIRouter(tags=["notifications"])


@router.get("")
async def list_notifications(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    unread_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = uuid.UUID(current_user["sub"])
    notifs, total = await NotificationService.get_user_notifications(
        db, user_id, page=page, limit=limit, unread_only=unread_only,
    )
    total_pages = max(1, (total + limit - 1) // limit) if total else 0
    return PaginatedResponse(
        success=True,
        data=[_notif_to_out(n) for n in notifs],
        meta=PaginatedMeta(page=page, limit=limit, total=total, total_pages=total_pages),
    )


@router.get("/unread-count")
async def unread_count(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = uuid.UUID(current_user["sub"])
    count = await NotificationService.get_unread_count(db, user_id)
    return SuccessResponse(data=UnreadCountResponse(count=count))


@router.patch("/{id}/read")
async def mark_as_read(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = uuid.UUID(current_user["sub"])
    notif = await NotificationService.mark_as_read(db, id, user_id)
    return SuccessResponse(data=_notif_to_out(notif))


@router.patch("/read-all")
async def mark_all_as_read(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = uuid.UUID(current_user["sub"])
    count = await NotificationService.mark_all_as_read(db, user_id)
    return SuccessResponse(data=MarkReadAllResponse(count=count))


def _notif_to_out(n) -> dict:
    return NotificationOut(
        id=str(n.id),
        type=n.type.value if hasattr(n.type, "value") else n.type,
        title=n.title,
        message=n.message,
        related_entity_type=n.related_entity_type,
        related_entity_id=str(n.related_entity_id) if n.related_entity_id else None,
        is_read=n.is_read,
        created_at=n.created_at,
    )
