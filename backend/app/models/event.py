import enum
import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, Text, Enum as SAEnum, Integer, ForeignKey, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base, TimestampMixin


class EventType(str, enum.Enum):
    IN_COLLEGE = "in_college"
    OUT_COLLEGE = "out_college"


class EventCategory(str, enum.Enum):
    VOLUNTEER = "volunteer"
    PARTICIPANT = "participant"
    BOTH = "both"


class EventStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class Event(TimestampMixin, Base):
    __tablename__ = "events"

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    event_type: Mapped[EventType] = mapped_column(SAEnum(EventType), nullable=False)
    category: Mapped[EventCategory] = mapped_column(SAEnum(EventCategory), nullable=False)
    status: Mapped[EventStatus] = mapped_column(SAEnum(EventStatus), default=EventStatus.DRAFT, nullable=False)
    venue: Mapped[str] = mapped_column(String(300), nullable=False)
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    max_registrations: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    coordinator_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, default=None)
    brochure_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    brochure_file_key: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    creator: Mapped["User"] = relationship(back_populates="events_created", foreign_keys=[created_by])
    coordinator: Mapped["User"] = relationship(back_populates="events_coordinated", foreign_keys=[coordinator_id])
    registrations: Mapped[List["Registration"]] = relationship(back_populates="event")
    attendance_records: Mapped[List["Attendance"]] = relationship(back_populates="event")

    __table_args__ = (
        Index("events_status_type_idx", "status", "event_type"),
        Index("events_coordinator_id_idx", "coordinator_id"),
        Index("events_created_by_idx", "created_by"),
        Index("events_start_date_idx", "start_date"),
    )
