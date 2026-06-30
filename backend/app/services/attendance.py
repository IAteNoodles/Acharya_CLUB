import uuid
from datetime import date
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.exceptions import NotFoundException, ForbiddenException, ConflictException
from app.models.event import Event
from app.models.attendance import Attendance, AttendanceStatus
from app.models.registration import Registration, RegistrationStatus


class AttendanceService:

    @staticmethod
    async def mark_bulk(
        db: AsyncSession,
        event_id: uuid.UUID,
        att_date: date,
        records: list[dict],
        current_user: dict,
    ) -> dict:
        event = await db.get(Event, event_id)
        if not event:
            raise NotFoundException(detail="Event not found")

        user_id = uuid.UUID(current_user["sub"])
        if current_user["role"] != "admin" and event.coordinator_id != user_id:
            raise ForbiddenException("You are not the coordinator of this event")

        student_ids = [r["studentId"] for r in records]
        reg_result = await db.execute(
            select(Registration).where(
                Registration.event_id == event_id,
                Registration.student_id.in_(student_ids),
                Registration.status == RegistrationStatus.ACCEPTED,
            )
        )
        registered_student_ids = {r.student_id for r in reg_result.scalars().all()}

        for r in records:
            if r["studentId"] not in registered_student_ids:
                raise ConflictException(f"Student {r['studentId']} is not registered for this event")

        count = 0
        for r in records:
            status = AttendanceStatus.PRESENT if r["present"] else AttendanceStatus.ABSENT

            existing = await db.execute(
                select(Attendance).where(
                    Attendance.event_id == event_id,
                    Attendance.student_id == r["studentId"],
                    Attendance.attendance_date == att_date,
                )
            )
            att = existing.scalar_one_or_none()
            if att:
                att.status = status
                att.marked_by = user_id
            else:
                att = Attendance(
                    event_id=event_id,
                    student_id=r["studentId"],
                    marked_by=user_id,
                    attendance_date=att_date,
                    status=status,
                )
                db.add(att)
            count += 1

        await db.commit()
        return {"count": count, "message": f"Attendance marked for {count} students"}

    @staticmethod
    async def get_event_attendance(
        db: AsyncSession,
        event_id: uuid.UUID,
        current_user: dict,
        att_date: Optional[date] = None,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[Attendance], int]:
        event = await db.get(Event, event_id)
        if not event:
            raise NotFoundException(detail="Event not found")

        user_id = uuid.UUID(current_user["sub"])
        if current_user["role"] != "admin" and event.coordinator_id != user_id:
            raise ForbiddenException("You are not the coordinator of this event")

        stmt = (
            select(Attendance)
            .options(joinedload(Attendance.student), joinedload(Attendance.marker))
            .where(Attendance.event_id == event_id)
        )
        count_stmt = select(func.count()).select_from(Attendance).where(Attendance.event_id == event_id)

        if att_date:
            stmt = stmt.where(Attendance.attendance_date == att_date)
            count_stmt = count_stmt.where(Attendance.attendance_date == att_date)

        count_result = await db.execute(count_stmt)
        total = count_result.scalar_one()

        stmt = (
            stmt
            .order_by(Attendance.attendance_date.desc(), Attendance.student_id)
            .offset((page - 1) * limit)
            .limit(limit)
        )

        result = await db.execute(stmt)
        records = list(result.scalars().all())

        return records, total

    @staticmethod
    async def get_student_attendance(
        db: AsyncSession,
        student_id: str,
        event_id: Optional[uuid.UUID] = None,
        status_filter: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[Attendance], int]:
        stmt = (
            select(Attendance)
            .options(joinedload(Attendance.event))
            .where(Attendance.student_id == student_id)
        )
        count_stmt = select(func.count()).select_from(Attendance).where(Attendance.student_id == student_id)

        if event_id:
            stmt = stmt.where(Attendance.event_id == event_id)
            count_stmt = count_stmt.where(Attendance.event_id == event_id)

        if status_filter:
            stmt = stmt.where(Attendance.status == status_filter)
            count_stmt = count_stmt.where(Attendance.status == status_filter)

        count_result = await db.execute(count_stmt)
        total = count_result.scalar_one()

        stmt = (
            stmt
            .order_by(Attendance.attendance_date.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )

        result = await db.execute(stmt)
        records = list(result.scalars().all())

        return records, total
