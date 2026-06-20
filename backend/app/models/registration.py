import enum
import uuid
from datetime import datetime
from sqlalchemy import Enum as SAEnum, ForeignKey, UniqueConstraint, Index, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base, TimestampMixin


class RegistrationRole(str, enum.Enum):
    VOLUNTEER = "volunteer"
    PARTICIPANT = "participant"


class RegistrationStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class Registration(TimestampMixin, Base):
    __tablename__ = "registrations"

    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=False)
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    role_type: Mapped[RegistrationRole] = mapped_column(SAEnum(RegistrationRole), nullable=False)
    status: Mapped[RegistrationStatus] = mapped_column(SAEnum(RegistrationStatus), default=RegistrationStatus.PENDING, nullable=False)
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    event: Mapped["Event"] = relationship(back_populates="registrations")
    student: Mapped["User"] = relationship(back_populates="registrations")

    __table_args__ = (
        UniqueConstraint("event_id", "student_id", "role_type", name="uq_reg_event_student_role"),
        Index("reg_student_id_idx", "student_id"),
        Index("reg_event_status_idx", "event_id", "status"),
    )
