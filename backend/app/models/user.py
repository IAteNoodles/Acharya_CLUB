import enum
from typing import List
from sqlalchemy import String, Text, Enum as SAEnum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin


class Role(str, enum.Enum):
    STUDENT = "student"
    TEACHER = "teacher"
    ADMIN = "admin"


class UserStatus(str, enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    REJECTED = "rejected"


class User(TimestampMixin, Base):
    __tablename__ = "users"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(180), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[Role] = mapped_column(SAEnum(Role, values_callable=lambda obj: [e.value for e in obj]), default=Role.STUDENT, nullable=False)
    status: Mapped[UserStatus] = mapped_column(SAEnum(UserStatus, values_callable=lambda obj: [e.value for e in obj]), default=UserStatus.PENDING, nullable=False)

    events_created: Mapped[List["Event"]] = relationship(
        back_populates="creator", foreign_keys="Event.created_by"
    )
    events_coordinated: Mapped[List["Event"]] = relationship(
        back_populates="coordinator", foreign_keys="Event.coordinator_id"
    )
    registrations: Mapped[List["Registration"]] = relationship(back_populates="student")
    attendance_marks: Mapped[List["Attendance"]] = relationship(
        back_populates="marker", foreign_keys="Attendance.marked_by"
    )

    __table_args__ = (
        Index("users_role_status_idx", "role", "status"),
    )
