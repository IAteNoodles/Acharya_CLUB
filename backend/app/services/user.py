import uuid
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.users import UserOut, PendingTeachersResponse, TeacherListResponse
from app.services.notification import NotificationService, NotificationType, _render_notification


def _compute_pagination(page: int, limit: int, total: int):
    total_pages = (total + limit - 1) // limit if total > 0 else 0
    return total_pages


async def get_pending_teachers(
    db: AsyncSession,
    page: int = 1,
    limit: int = 20,
) -> PendingTeachersResponse:
    from app.models.user import User

    offset = (page - 1) * limit

    stmt = (
        select(User)
        .where(User.role == "teacher", User.status == "pending")
        .offset(offset)
        .limit(limit)
        .order_by(User.created_at.asc())
    )
    count_stmt = (
        select(func.count(User.id))
        .where(User.role == "teacher", User.status == "pending")
    )

    result = await db.execute(stmt)
    users = result.scalars().all()

    count_result = await db.execute(count_stmt)
    total = count_result.scalar() or 0

    total_pages = _compute_pagination(page, limit, total)

    return PendingTeachersResponse(
        users=[UserOut.model_validate(u) for u in users],
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages,
    )


async def _get_teacher_user(db: AsyncSession, user_id: str):
    from app.models.user import User

    try:
        uuid.UUID(user_id)
    except ValueError:
        return None

    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def approve_teacher(db: AsyncSession, user_id: str) -> UserOut:
    from fastapi import HTTPException

    user = await _get_teacher_user(db, user_id)

    if not user or user.role != "teacher":
        raise HTTPException(status_code=404, detail="User not found")

    if user.status == "active":
        raise HTTPException(status_code=409, detail="User is already active")

    if user.status == "rejected":
        raise HTTPException(status_code=409, detail="User is already rejected")

    user.status = "active"
    title, message = _render_notification(NotificationType.TEACHER_APPROVED)
    await NotificationService.create_notification(
        db,
        user_id=user.id,
        notif_type=NotificationType.TEACHER_APPROVED,
        title=title,
        message=message,
        entity_type="user",
        entity_id=user.id,
    )
    await db.commit()
    await db.refresh(user)

    return UserOut.model_validate(user)


async def reject_teacher(db: AsyncSession, user_id: str) -> UserOut:
    from fastapi import HTTPException

    user = await _get_teacher_user(db, user_id)

    if not user or user.role != "teacher":
        raise HTTPException(status_code=404, detail="User not found")

    if user.status == "rejected":
        raise HTTPException(status_code=409, detail="User is already rejected")

    user.status = "rejected"
    title, message = _render_notification(NotificationType.TEACHER_REJECTED)
    await NotificationService.create_notification(
        db,
        user_id=user.id,
        notif_type=NotificationType.TEACHER_REJECTED,
        title=title,
        message=message,
        entity_type="user",
        entity_id=user.id,
    )
    await db.commit()
    await db.refresh(user)

    return UserOut.model_validate(user)


async def get_active_teachers(
    db: AsyncSession,
    page: int = 1,
    limit: int = 20,
    search: str | None = None,
) -> TeacherListResponse:
    from app.models.user import User

    offset = (page - 1) * limit

    base_filters = [User.role == "teacher", User.status == "active"]

    if search:
        search_filter = or_(
            User.name.ilike(f"%{search}%"),
            User.email.ilike(f"%{search}%"),
        )
        stmt = (
            select(User)
            .where(*base_filters, search_filter)
            .offset(offset)
            .limit(limit)
            .order_by(User.name.asc())
        )
        count_stmt = (
            select(func.count(User.id))
            .where(*base_filters, search_filter)
        )
    else:
        stmt = (
            select(User)
            .where(*base_filters)
            .offset(offset)
            .limit(limit)
            .order_by(User.name.asc())
        )
        count_stmt = (
            select(func.count(User.id))
            .where(*base_filters)
        )

    result = await db.execute(stmt)
    users = result.scalars().all()

    count_result = await db.execute(count_stmt)
    total = count_result.scalar() or 0

    total_pages = _compute_pagination(page, limit, total)

    return TeacherListResponse(
        users=[UserOut.model_validate(u) for u in users],
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages,
    )
