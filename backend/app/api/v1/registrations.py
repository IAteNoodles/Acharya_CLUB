import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_student, require_teacher_or_admin
from app.core.database import get_db
from app.schemas.common import SuccessResponse, PaginatedResponse, PaginatedMeta
from app.schemas.registration import (
    EventBrief,
    RegisterRequest,
    RegistrationResponse,
    RegistrationWithEventResponse,
    RegistrationWithStudentResponse,
    StudentBrief,
)
from app.services.registration import RegistrationService

router = APIRouter(prefix="/api/v1/registrations", tags=["registrations"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def register_for_event(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_student),
):
    reg = await RegistrationService.register(
        db, request.event_id, request.role_type.value if hasattr(request.role_type, "value") else request.role_type, current_user,
    )
    return SuccessResponse(data=_reg_to_response(reg))


@router.get("/my")
async def get_my_registrations(
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_student),
):
    registrations, total = await RegistrationService.get_student_registrations(
        db, current_user["sub"], status_filter=status_filter, page=page, limit=limit,
    )
    total_pages = max(1, (total + limit - 1) // limit) if total else 0
    return PaginatedResponse(
        success=True,
        data=[_reg_to_event_response(r) for r in registrations],
        meta=PaginatedMeta(page=page, limit=limit, total=total, total_pages=total_pages),
    )


@router.get("/event/{event_id}")
async def get_event_registrations(
    event_id: uuid.UUID,
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_teacher_or_admin),
):
    registrations, total = await RegistrationService.get_event_registrations(
        db, event_id, current_user,
        status_filter=status_filter, page=page, limit=limit,
    )
    total_pages = max(1, (total + limit - 1) // limit) if total else 0
    return PaginatedResponse(
        success=True,
        data=[_reg_to_student_response(r) for r in registrations],
        meta=PaginatedMeta(page=page, limit=limit, total=total, total_pages=total_pages),
    )


@router.patch("/{id}/accept")
async def accept_registration(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_teacher_or_admin),
):
    reg = await RegistrationService.accept_registration(db, id, current_user)
    return SuccessResponse(data=_reg_to_response(reg))


@router.patch("/{id}/reject")
async def reject_registration(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_teacher_or_admin),
):
    reg = await RegistrationService.reject_registration(db, id, current_user)
    return SuccessResponse(data=_reg_to_response(reg))


def _reg_to_response(reg) -> dict:
    return RegistrationResponse(
        id=str(reg.id),
        event_id=str(reg.event_id),
        student_id=str(reg.student_id),
        role_type=reg.role_type.value if hasattr(reg.role_type, "value") else reg.role_type,
        status=reg.status.value if hasattr(reg.status, "value") else reg.status,
        registered_at=reg.registered_at,
        updated_at=reg.updated_at,
    )


def _reg_to_event_response(reg) -> dict:
    event = reg.event
    return RegistrationWithEventResponse(
        id=str(reg.id),
        event_id=str(reg.event_id),
        role_type=reg.role_type.value if hasattr(reg.role_type, "value") else reg.role_type,
        status=reg.status.value if hasattr(reg.status, "value") else reg.status,
        registered_at=reg.registered_at,
        event=EventBrief(
            id=str(event.id),
            title=event.title,
            event_type=event.event_type.value if hasattr(event.event_type, "value") else event.event_type,
            start_date=event.start_date,
            end_date=event.end_date,
        ),
    )


def _reg_to_student_response(reg) -> dict:
    student = reg.student
    return RegistrationWithStudentResponse(
        id=str(reg.id),
        event_id=str(reg.event_id),
        role_type=reg.role_type.value if hasattr(reg.role_type, "value") else reg.role_type,
        status=reg.status.value if hasattr(reg.status, "value") else reg.status,
        registered_at=reg.registered_at,
        student=StudentBrief(
            id=str(student.id),
            name=student.name,
            email=student.email,
        ),
    )
