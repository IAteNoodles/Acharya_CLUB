# Acharya_CLUB — Database Schema Document

## 1. Database Selection: SQLite

SQLite is used for local-first zero-config development. It provides full ACID compliance and stores data in a single local file (`acharya_club.db`).

### Database Engine Configuration

SQLAlchemy's async engine uses `aiosqlite` as the driver. The engine sets WAL (Write-Ahead Logging) mode and normal synchronization on connection to optimize concurrency and performance:

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import event

engine = create_async_engine(
    "sqlite+aiosqlite:///./acharya_club.db",
    echo=False,
)

@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
```

---

## 2. Entity-Relationship Overview

### Text Diagram

```
┌───────────────┐       ┌──────────────────┐
│     User      │       │      Event       │
│───────────────│       │──────────────────│
│ id (PK)       │1──N   │ id (PK)          │
│ name          │◄──────│ created_by (FK)  │
│ email         │created│ coordinator (FK) │
│ password_hash │       │ title            │
│ role          │       │ description      │
│ status        │       │ start_date       │
│ created_at    │       │ end_date         │
│ updated_at    │       │ venue            │
└───────┬───────┘       │ type             │
        │               │ category         │
        │               │ status           │
        │               │ max_registrations│
        │1              │ created_at       │
        │               │ updated_at       │
        │               └────────┬─────────┘
        │                        │
        │1──N                    │1
        │  registered            │  belongs to
        │  by                    │
        │                        │
        │  ┌─────────────────────┴──────────┐
        │  │         Registration           │
        │  │───────────────────────────────│
        │  │ id (PK)                       │
        │  │ event_id (FK)                 │
        │  ├──│ student_id (FK)               │
        │  │ role_type                     │
        │  │ status                        │
        │  │ registered_at                 │
        │  │ updated_at                    │
        │  │                              │
        │  │ UNIQUE(event_id, student_id,  │
        │  │         role_type)            │
        │  └───────────────────────────────┘
        │
        │  ┌──────────────────────────────┐
        │  │         Attendance           │
        │  │─────────────────────────────│
        │  │ id (PK)                     │
        │  │ event_id (FK)               │
        │  ├──│ student_id (FK)             │
        │  │ marked_by (FK)              │
        │  │ date                        │
        │  │ status                      │
        │  │ marked_at                   │
        │  │                             │
        │  │ UNIQUE(event_id, student_id,│
        │  │         date)               │
        │  └─────────────────────────────┘
```

---

## 3. SQLAlchemy 2.0 Declarative Models

All models inherit from `Base` and `TimestampMixin` defined in `app/models/base.py`:

```python
import uuid
from datetime import datetime
from sqlalchemy import DateTime, func, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class TimestampMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
```

### 3.1 Model: User (`users`)

```python
class User(TimestampMixin, Base):
    __tablename__ = "users"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(180), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[Role] = mapped_column(SAEnum(Role), default=Role.STUDENT, nullable=False)
    status: Mapped[UserStatus] = mapped_column(SAEnum(UserStatus), default=UserStatus.PENDING, nullable=False)
```

### 3.2 Model: Event (`events`)

```python
class Event(TimestampMixin, Base):
    __tablename__ = "events"

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_type: Mapped[EventType] = mapped_column(SAEnum(EventType), nullable=False)
    category: Mapped[EventCategory] = mapped_column(SAEnum(EventCategory), nullable=False)
    status: Mapped[EventStatus] = mapped_column(SAEnum(EventStatus), default=EventStatus.DRAFT, nullable=False)
    venue: Mapped[str] = mapped_column(String(300), nullable=False)
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    max_registrations: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    coordinator_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True)
```

### 3.3 Model: Registration (`registrations`)

```python
class Registration(TimestampMixin, Base):
    __tablename__ = "registrations"

    event_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("events.id"), nullable=False)
    student_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    role_type: Mapped[RegistrationRole] = mapped_column(SAEnum(RegistrationRole), nullable=False)
    status: Mapped[RegistrationStatus] = mapped_column(SAEnum(RegistrationStatus), default=RegistrationStatus.PENDING, nullable=False)
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
```

### 3.4 Model: Attendance (`attendance`)

```python
class Attendance(TimestampMixin, Base):
    __tablename__ = "attendance"

    event_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("events.id"), nullable=False)
    student_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    marked_by: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    attendance_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[AttendanceStatus] = mapped_column(SAEnum(AttendanceStatus), default=AttendanceStatus.PRESENT, nullable=False)
    marked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
```

### 3.5 Model: Notification (`notifications`)

```python
class Notification(TimestampMixin, Base):
    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    type: Mapped[NotificationType] = mapped_column(SAEnum(NotificationType), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    related_entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    related_entity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
```

---

## 4. Indexing & Unique Constraints

| Table | Index / Constraint Name | Columns | Type | Unique | Rationale |
|---|---|---|---|---|---|
| `users` | `ix_users_email` | `(email)` | B-tree | Yes | Fast authentication lookup by email. |
| `users` | `users_role_status_idx` | `(role, status)` | B-tree | No | Administrative queries filtering users by role and status. |
| `events` | `events_status_type_idx` | `(status, event_type)` | B-tree | No | Event listing filtering by status and event type. |
| `events` | `events_coordinator_id_idx` | `(coordinator_id)` | B-tree | No | Event filtering for assigned coordinators. |
| `events` | `events_created_by_idx` | `(created_by)` | B-tree | No | Event filtering by event creators. |
| `events` | `events_start_date_idx` | `(start_date)` | B-tree | No | Event calendars sorting and date range queries. |
| `registrations` | `uq_reg_event_student_role` | `(event_id, student_id, role_type)` | B-tree | Yes | Prevents duplicate student registrations for the same event and role. |
| `registrations` | `reg_event_status_idx` | `(event_id, status)` | B-tree | No | Listing and filtering registrations for a specific event. |
| `registrations` | `reg_student_id_idx` | `(student_id)` | B-tree | No | Listing registration history for a specific student. |
| `attendance` | `uq_att_event_student_date` | `(event_id, student_id, attendance_date)` | B-tree | Yes | Enforces one attendance record per student per event per day. |
| `attendance` | `att_event_date_idx` | `(event_id, attendance_date)` | B-tree | No | Fetching attendance sheets for an event on a specific date. |
| `attendance` | `att_student_id_idx` | `(student_id)` | B-tree | No | Fetching attendance history for a specific student. |

---

## 5. Schema Generation

Schema is generated automatically on application startup using:
```python
Base.metadata.create_all(bind=engine)
```
No migrations framework (Alembic) is used, matching the local-first zero-config workflow.
