import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin, require_teacher_or_admin
from app.core.database import get_db
from app.schemas.common import SuccessResponse, PaginatedResponse, PaginatedMeta
from app.schemas.attendance import (
    AttendanceWithStudentResponse,
    AttendanceWithEventResponse,
    BulkAttendanceRequest,
    BulkAttendanceResponse,
    StudentBrief,
    MarkerBrief,
)
from app.services.attendance import AttendanceService

router = APIRouter(prefix="/api/v1/attendance", tags=["Attendance"])


@router.post("/bulk")
async def mark_bulk_attendance(
    request: BulkAttendanceRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_teacher_or_admin),
):
    records_dict = [{"studentId": r.studentId, "present": r.present} for r in request.records]
    result = await AttendanceService.mark_bulk(
        db, request.eventId, request.date, records_dict, current_user,
    )
    return SuccessResponse(data=BulkAttendanceResponse(**result))


@router.get("/event/{event_id}")
async def get_event_attendance(
    event_id: uuid.UUID,
    att_date: Optional[date] = Query(None, alias="date"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_teacher_or_admin),
):
    records, total = await AttendanceService.get_event_attendance(
        db, event_id, current_user, att_date=att_date, page=page, limit=limit,
    )
    total_pages = max(1, (total + limit - 1) // limit) if total else 0
    return PaginatedResponse(
        success=True,
        data=[_att_to_student_response(r) for r in records],
        meta=PaginatedMeta(page=page, limit=limit, total=total, total_pages=total_pages),
    )


@router.get("/my")
async def get_my_attendance(
    event_id: Optional[uuid.UUID] = Query(None, alias="eventId"),
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    records, total = await AttendanceService.get_student_attendance(
        db, current_user["sub"], event_id=event_id, status_filter=status_filter,
        page=page, limit=limit,
    )
    total_pages = max(1, (total + limit - 1) // limit) if total else 0
    return PaginatedResponse(
        success=True,
        data=[_att_to_event_response(r) for r in records],
        meta=PaginatedMeta(page=page, limit=limit, total=total, total_pages=total_pages),
    )


@router.get("/student/{student_id}")
async def get_student_attendance(
    student_id: uuid.UUID,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    records, total = await AttendanceService.get_student_attendance(
        db, str(student_id), page=page, limit=limit,
    )
    total_pages = max(1, (total + limit - 1) // limit) if total else 0
    return PaginatedResponse(
        success=True,
        data=[_att_to_event_response(r) for r in records],
        meta=PaginatedMeta(page=page, limit=limit, total=total, total_pages=total_pages),
    )


def _att_to_student_response(att) -> AttendanceWithStudentResponse:
    student = att.student if hasattr(att, "student") and att.student else None
    marker = att.marker if hasattr(att, "marker") and att.marker else None
    return AttendanceWithStudentResponse(
        id=str(att.id),
        event_id=str(att.event_id),
        student_id=str(att.student_id),
        date=att.attendance_date,
        status=att.status.value if hasattr(att.status, "value") else att.status,
        student=StudentBrief(id=str(student.id), name=student.name, email=student.email) if student else None,
        marked_by=MarkerBrief(id=str(marker.id), name=marker.name) if marker else None,
    )


def _att_to_event_response(att) -> AttendanceWithEventResponse:
    event = att.event if hasattr(att, "event") and att.event else None
    return AttendanceWithEventResponse(
        id=str(att.id),
        event_id=str(att.event_id),
        student_id=str(att.student_id),
        date=att.attendance_date,
        status=att.status.value if hasattr(att.status, "value") else att.status,
        event={
            "id": str(event.id),
            "title": event.title,
            "event_type": event.event_type.value if hasattr(event.event_type, "value") else event.event_type,
            "start_date": str(event.start_date),
            "end_date": str(event.end_date),
        } if event else None,
    )
