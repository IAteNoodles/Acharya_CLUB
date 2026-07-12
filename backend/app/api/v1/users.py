from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.api import deps
from app.core.database import get_db
from app.schemas.users import (
    PendingTeachersResponse,
    TeacherListResponse,
    UserActionResponse,
)
from app.services import user as user_service

router = APIRouter(tags=["users"])


@router.get(
    "/pending-teachers",
    response_model=PendingTeachersResponse,
    dependencies=[Depends(deps.require_admin)],
)
async def get_pending_teachers(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    return await user_service.get_pending_teachers(db, page=page, limit=limit)


@router.patch(
    "/{id}/approve",
    response_model=UserActionResponse,
    dependencies=[Depends(deps.require_admin)],
)
async def approve_teacher(
    id: str,
    db: AsyncSession = Depends(get_db),
):
    user = await user_service.approve_teacher(db, id)
    return UserActionResponse(data=user)


@router.patch(
    "/{id}/reject",
    response_model=UserActionResponse,
    dependencies=[Depends(deps.require_admin)],
)
async def reject_teacher(
    id: str,
    db: AsyncSession = Depends(get_db),
):
    user = await user_service.reject_teacher(db, id)
    return UserActionResponse(data=user)


@router.get(
    "/teachers",
    response_model=TeacherListResponse,
    dependencies=[Depends(deps.require_admin)],
)
async def get_teachers(
    search: str | None = Query(None, max_length=180),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    return await user_service.get_active_teachers(
        db, page=page, limit=limit, search=search,
    )
