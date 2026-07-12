import enum
import uuid
from datetime import date, datetime
from sqlalchemy import Enum as SAEnum, ForeignKey, Date, UniqueConstraint, Index, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base, TimestampMixin


class AttendanceStatus(str, enum.Enum):
    PRESENT = "present"
    ABSENT = "absent"


class Attendance(TimestampMixin, Base):
    __tablename__ = "attendance"

    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=False)
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    marked_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    attendance_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[AttendanceStatus] = mapped_column(SAEnum(AttendanceStatus, values_callable=lambda obj: [e.value for e in obj]), default=AttendanceStatus.PRESENT, nullable=False)
    marked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    event: Mapped["Event"] = relationship(back_populates="attendance_records")
    student: Mapped["User"] = relationship(foreign_keys=[student_id])
    marker: Mapped["User"] = relationship(back_populates="attendance_marks", foreign_keys=[marked_by])

    __table_args__ = (
        UniqueConstraint("event_id", "student_id", "attendance_date", name="uq_att_event_student_date"),
        Index("att_event_date_idx", "event_id", "attendance_date"),
        Index("att_student_id_idx", "student_id"),
    )
