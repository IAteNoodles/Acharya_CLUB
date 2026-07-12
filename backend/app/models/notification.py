import enum
import uuid
from typing import Optional
from sqlalchemy import String, Text, Boolean, Enum as SAEnum, ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin


class NotificationType(str, enum.Enum):
    REGISTRATION_ACCEPTED = "registration_accepted"
    REGISTRATION_REJECTED = "registration_rejected"
    EVENT_APPROVED = "event_approved"
    EVENT_REJECTED = "event_rejected"
    TEACHER_APPROVED = "teacher_approved"
    TEACHER_REJECTED = "teacher_rejected"


class Notification(TimestampMixin, Base):
    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    type: Mapped[NotificationType] = mapped_column(
        SAEnum(NotificationType, values_callable=lambda obj: [e.value for e in obj]), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    related_entity_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    related_entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), nullable=True
    )
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
