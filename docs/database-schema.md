# Acharya_CLUB — Database Schema Document

## 1. Database Selection: PostgreSQL 16

### Rationale

| Factor | PostgreSQL 16 | Why It Matters |
|---|---|---|
| **ACID Compliance** | Full ACID with configurable isolation levels (Read Committed default, Serializable available) | Registration transactions, attendance bulk upserts, and event approval workflows must be atomic — a partial failure (e.g., registration saved but capacity not decremented) would corrupt system state. |
| **JSON Support** | JSONB with GIN indexes for indexing inside JSON documents | Event metadata, student profile extras, and configurable form fields can live in JSONB columns without requiring schema migrations for every new field. |
| **Strong Typing** | Strict type system with domains, enums, and custom types | Enums for `Role`, `EventType`, `RegistrationStatus` prevent invalid data at the database level — not just the application layer. |
| **Indexing** | B-tree, Hash, GiST, GIN, SP-GiST, BRIN, bloom | Composite B-tree indexes for the most common query patterns (event feed filtering, registration lookups). BRIN indexes for large, append-only audit logs ordered by timestamp. |
| **Reliability** | Point-in-time recovery, WAL archiving, streaming replication, online DDL (pg_repack) | Production data is critical for a college system — attendance records and registration data must survive hardware failures. PITR guarantees recovery to any second. |
| **Maturity** | First release 1996, current 16.x | Battle-tested in production across every scale. Extensive documentation, tooling, and community support. SQLAlchemy's PostgreSQL dialect is the most mature of all its supported backends. |

### Connection Pooling via asyncpg + SQLAlchemy

SQLAlchemy's async engine uses `asyncpg` as the PostgreSQL driver. Connection pooling is configured through `create_async_engine`:

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

engine = create_async_engine(
    "postgresql+asyncpg://user:password@host:5432/acharya",
    pool_size=15,
    max_overflow=5,
    pool_timeout=30,
    pool_pre_ping=True,
    echo=False,
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
```

Connection string format: `postgresql+asyncpg://user:password@host:5432/acharya`

| Parameter | Value | Description |
|---|---|---|
| `pool_size` | 15 | Number of connections to maintain in the pool |
| `max_overflow` | 5 | Additional connections allowed beyond pool_size |
| `pool_timeout` | 30 | Seconds to wait for a connection before raising an error |
| `pool_pre_ping` | true | Verify connection liveness before checkout |

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
        ├──│ student_id (FK)               │
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
        ├──│ student_id (FK)             │
        │  │ marked_by (FK)              │
        │  │ date                        │
        │  │ status                      │
        │  │ marked_at                   │
        │  │                             │
        │  │ UNIQUE(event_id, student_id,│
        │  │         date)               │
        │  └─────────────────────────────┘
```

### Relationship Summary

| Left Entity | Relationship | Right Entity | Cardinality | Description |
|---|---|---|---|---|
| User | created_by → | Event | 1:N | A user (teacher/admin) can create many events |
| User | coordinator → | Event | 1:N | A user (teacher) can coordinate many events |
| User | → | Registration | 1:N | A user (student) can register for many events |
| User | → | Attendance | 1:N | A user (teacher) can mark many attendance records |
| Event | → | Registration | 1:N | An event can have many registrations |
| Event | → | Attendance | 1:N | An event can have many attendance records |

---

## 3. Complete Schema (SQLAlchemy 2.0 Async)

### Model Directory Structure

```
app/
├── models/
│   ├── __init__.py
│   ├── base.py
│   ├── user.py
│   ├── event.py
│   ├── registration.py
│   └── attendance.py
└── core/
    ├── database.py
    └── security.py
```

### Base Model: `app/models/base.py`

```python
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass
```

### Database Session: `app/core/database.py`

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

DATABASE_URL = "postgresql+asyncpg://user:password@host:5432/acharya"

engine = create_async_engine(
    DATABASE_URL,
    pool_size=15,
    max_overflow=5,
    pool_timeout=30,
    pool_pre_ping=True,
    echo=False,
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

### Enums

```python
# ──────────────────────────────────────────────
# Enums: app/models/enums.py
# ──────────────────────────────────────────────

import enum


class Role(str, enum.Enum):
    STUDENT = "student"
    TEACHER = "teacher"
    ADMIN = "admin"


class UserStatus(str, enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    REJECTED = "rejected"


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


class RegistrationRole(str, enum.Enum):
    VOLUNTEER = "volunteer"
    PARTICIPANT = "participant"


class RegistrationStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class AttendanceStatus(str, enum.Enum):
    PRESENT = "present"
    ABSENT = "absent"
    LATE = "late"
```

### Model: User — `app/models/user.py`

```python
import uuid
import datetime

from sqlalchemy import String, Enum, DateTime, Text, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import Role, UserStatus


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(
        String(180), unique=True, nullable=False, index=True
    )
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[Role] = mapped_column(
        Enum(Role), default=Role.STUDENT, nullable=False
    )
    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus), default=UserStatus.PENDING, nullable=False
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.datetime.utcnow
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )

    # ── Relations ──────────────────────────────────────
    events_created = relationship(
        "Event", back_populates="creator", foreign_keys="Event.created_by_id"
    )
    events_coordinated = relationship(
        "Event", back_populates="coordinator", foreign_keys="Event.coordinator_id"
    )
    registrations = relationship("Registration", back_populates="student")
    attendance_marks = relationship(
        "Attendance", back_populates="marker", foreign_keys="Attendance.marked_by_id"
    )

    __table_args__ = (
        Index("ix_users_role_status", "role", "status"),
    )

    def __repr__(self) -> str:
        return f"<User {self.email}>"
```

### Model: Event — `app/models/event.py`

```python
import uuid
import datetime

from sqlalchemy import String, Enum, DateTime, Text, Integer, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import EventType, EventCategory, EventStatus


class Event(Base):
    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    type: Mapped[EventType] = mapped_column(
        Enum(EventType), nullable=False
    )
    category: Mapped[EventCategory] = mapped_column(
        Enum(EventCategory), nullable=False
    )
    status: Mapped[EventStatus] = mapped_column(
        Enum(EventStatus), default=EventStatus.DRAFT, nullable=False
    )
    venue: Mapped[str] = mapped_column(String(300), nullable=False)
    start_date: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    end_date: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    max_registrations: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    coordinator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.datetime.utcnow
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )

    # ── Relations ──────────────────────────────────────
    creator = relationship(
        "User", back_populates="events_created", foreign_keys=[created_by_id]
    )
    coordinator = relationship(
        "User", back_populates="events_coordinated", foreign_keys=[coordinator_id]
    )
    registrations = relationship("Registration", back_populates="event")
    attendance = relationship("Attendance", back_populates="event")

    __table_args__ = (
        Index("ix_events_status_type", "status", "type"),
        Index("ix_events_coordinator_id", "coordinator_id"),
        Index("ix_events_created_by_id", "created_by_id"),
        Index("ix_events_start_date", "start_date"),
    )

    def __repr__(self) -> str:
        return f"<Event {self.title}>"
```

### Model: Registration — `app/models/registration.py`

```python
import uuid
import datetime

from sqlalchemy import Enum, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import RegistrationRole, RegistrationStatus


class Registration(Base):
    __tablename__ = "registrations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("events.id"), nullable=False
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    role_type: Mapped[RegistrationRole] = mapped_column(
        Enum(RegistrationRole), nullable=False
    )
    status: Mapped[RegistrationStatus] = mapped_column(
        Enum(RegistrationStatus), default=RegistrationStatus.PENDING, nullable=False
    )
    registered_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.datetime.utcnow
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )

    # ── Relations ──────────────────────────────────────
    event = relationship("Event", back_populates="registrations")
    student = relationship("User", back_populates="registrations")

    __table_args__ = (
        UniqueConstraint(
            "event_id",
            "student_id",
            "role_type",
            name="uq_registrations_event_student_role",
        ),
        Index("ix_registrations_student_id", "student_id"),
        Index("ix_registrations_event_status", "event_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<Registration {self.event_id} {self.student_id} {self.role_type}>"
```

### Model: Attendance — `app/models/attendance.py`

```python
import uuid
import datetime

from sqlalchemy import Enum, DateTime, Date, ForeignKey, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import AttendanceStatus


class Attendance(Base):
    __tablename__ = "attendance"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("events.id"), nullable=False
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    marked_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    status: Mapped[AttendanceStatus] = mapped_column(
        Enum(AttendanceStatus), default=AttendanceStatus.PRESENT, nullable=False
    )
    marked_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.datetime.utcnow
    )

    # ── Relations ──────────────────────────────────────
    event = relationship("Event", back_populates="attendance")
    student = relationship("User", foreign_keys=[student_id])
    marker = relationship(
        "User", back_populates="attendance_marks", foreign_keys=[marked_by_id]
    )

    __table_args__ = (
        UniqueConstraint(
            "event_id", "student_id", "date", name="uq_attendance_event_student_date"
        ),
        Index("ix_attendance_event_date", "event_id", "date"),
        Index("ix_attendance_student_id", "student_id"),
    )

    def __repr__(self) -> str:
        return f"<Attendance {self.event_id} {self.student_id} {self.date}>"
```

---

## 4. Complete Schema Summary

### Full File: `app/models/__init__.py`

```python
from app.models.base import Base
from app.models.enums import (
    Role,
    UserStatus,
    EventType,
    EventCategory,
    EventStatus,
    RegistrationRole,
    RegistrationStatus,
    AttendanceStatus,
)
from app.models.user import User
from app.models.event import Event
from app.models.registration import Registration
from app.models.attendance import Attendance

__all__ = [
    "Base",
    "Role",
    "UserStatus",
    "EventType",
    "EventCategory",
    "EventStatus",
    "RegistrationRole",
    "RegistrationStatus",
    "AttendanceStatus",
    "User",
    "Event",
    "Registration",
    "Attendance",
]
```

### Generated SQL Types

| SQLAlchemy Type | PostgreSQL Type | Notes |
|---|---|---|
| `UUID(as_uuid=True)` primary key | `uuid` | Primary key, generated by `uuid.uuid4()` |
| `String(n)` | `character varying(n)` | Variable-length string with max length |
| `Text` | `text` | Unlimited-length string |
| `DateTime(timezone=True)` | `timestamptz` | Timezone-aware timestamp |
| `Date` | `date` | Date only (no time component), used for attendance.date |
| `Integer` | `integer` | 4-byte signed integer |
| `Enum(EventType)` | `eventtype` | Custom enum type created via `CREATE TYPE eventtype AS ENUM('in_college','out_college')` |
| `Boolean` | `boolean` | Not used currently but available for future flags |

---

## 5. Index Strategy Table

| Table | Index Name | Columns | Type | Unique | Rationale |
|---|---|---|---|---|---|
| `users` | `ix_users_role_status` | `(role, status)` | B-tree | No | Admin screens filter teachers by approval status (e.g., "show all pending teachers"). The leading `role` column filters the role first, then `status` further narrows. This covers queries like `WHERE role = 'teacher' AND status = 'pending'`. |
| `users` | — (auto from `unique=True`) | `(email)` | B-tree | Yes | Login authentication always looks up a user by email. The unique constraint is enforced at the database level to prevent duplicate registrations. A B-tree on email gives O(log n) lookup — fast even for tens of thousands of users. |
| `events` | `ix_events_status_type` | `(status, type)` | B-tree | No | The primary student event feed query: "show all approved in-college events". With `status` as the leading column, the index efficiently narrows to approved events first, then filters by type. |
| `events` | `ix_events_coordinator_id` | `(coordinator_id)` | B-tree | No | Teachers see their assigned events: "show all events where I am the coordinator". The foreign key `coordinator_id` is a high-selectivity column (few rows per coordinator value), making a B-tree index very efficient. |
| `events` | `ix_events_created_by_id` | `(created_by_id)` | B-tree | No | Users view events they created. Also a foreign key index supporting the `User → Event` relation join. Essential for listing "my events" on dashboards. |
| `events` | `ix_events_start_date` | `(start_date)` | B-tree | No | Calendar views and date-range queries filter events by `start_date`. Also supports date-sorted listing (upcoming events first). Without this index, PostgreSQL would need to sort the full table. |
| `registrations` | `uq_registrations_event_student_role` | `(event_id, student_id, role_type)` | B-tree | Yes | Prevents duplicate registrations — a student cannot register for the same event with the same role twice. However, it permits registering as both `volunteer` and `participant` for the same event (different `role_type`). This is a business rule enforced at the database level. |
| `registrations` | `ix_registrations_student_id` | `(student_id)` | B-tree | No | Students view their registration history: "show all events I registered for". The foreign key index supports the `User → Registration` join. |
| `registrations` | `ix_registrations_event_status` | `(event_id, status)` | B-tree | No | Event coordinators filter registrations by status: "show all accepted registrations for my event". The composite index covers `WHERE event_id = X AND status = 'accepted'` without filtering in PostgreSQL. |
| `attendance` | `uq_attendance_event_student_date` | `(event_id, student_id, date)` | B-tree | Yes | Enforces one attendance record per student per event per day. For multi-day events, a student can have separate records for each day but not duplicate records on the same day. |
| `attendance` | `ix_attendance_event_date` | `(event_id, date)` | B-tree | No | Teachers load the attendance sheet for a specific event and date: "show all attendance records for event X on day Y". The leading `event_id` column narrows to the event, then `date` filters for the specific day. |
| `attendance` | `ix_attendance_student_id` | `(student_id)` | B-tree | No | Students view their attendance history across all events. The foreign key index supports the `User → Attendance` join and powers queries like "show my attendance records for the past semester". |

### Index Design Decisions

1. **Composite before single-column**: Wherever possible, composite indexes covering multiple query predicates are preferred over individual single-column indexes. PostgreSQL can use a composite index for queries on any prefix of the indexed columns (e.g., `(event_id, status)` covers `WHERE event_id = X` alone, but not `WHERE status = 'accepted'` alone). This reduces the total number of indexes and write amplification.

2. **No over-indexing**: Each additional index adds write overhead (INSERT/UPDATE/DELETE must update every index) and storage cost. Only indexes that support real query patterns are created. If query patterns change (monitored via `pg_stat_user_indexes`), indexes can be added with `CREATE INDEX CONCURRENTLY` without downtime.

3. **Unique constraints as indexes**: PostgreSQL automatically creates a B-tree index for each unique constraint (`UniqueConstraint` in SQLAlchemy). These indexes serve double duty: they enforce data integrity and speed up queries on those columns.

4. **Foreign key indexes**: PostgreSQL does NOT automatically create indexes on foreign key columns. Each foreign key (`created_by_id`, `coordinator_id`, `event_id`, `student_id`, `marked_by_id`) has an explicit index (either standalone or as part of a composite) to support join performance.

5. **BRIN alternative considered**: For the `attendance` table which grows linearly with events, a BRIN index on `(event_id, date)` was considered (block range index is smaller and faster for physical-order-correlated data). However, B-tree was chosen because attendance data is not strictly inserted in chronological order (bulk imports, backdated corrections), and BRIN performs poorly when data is not physically correlated with the indexed columns.

---

## 6. Migration Strategy

### Alembic for Schema Versioning

All schema changes are managed through Alembic. The workflow ensures that every change is reviewed, versioned, and reversible.

### Installation & Setup

```bash
pip install alembic

# Initialize async Alembic
alembic init -t async alembic
```

This creates:
```
alembic/
├── env.py              # Async environment configuration
├── script.py.mako      # Migration template
└── versions/           # Migration scripts
alembic.ini             # Alembic configuration
```

### Configure `alembic.ini`

```ini
[alembic]
script_location = alembic
sqlalchemy.url = postgresql+asyncpg://user:password@host:5432/acharya
compare_type = true
compare_server_default = true
```

### Configure `alembic/env.py` (async)

```python
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.models.base import Base
from app.models import User, Event, Registration, Attendance  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

### Migration Commands

```bash
# Create initial migration
alembic revision --autogenerate -m "create_initial_tables"

# Apply migrations
alembic upgrade head

# Rollback one step
alembic downgrade -1

# View history
alembic history

# Check current revision
alembic current

# Show pending migrations
alembic upgrade --sql
```

### Migration Lifecycle

```
SQLAlchemy model change
        │
        ▼
  alembic revision --autogenerate
  (generates Python file in alembic/versions/)
        │
        ▼
  Code review of generated migration
  (ensure no unintended DropColumn or destructive changes)
        │
        ▼
  Commit migration + model changes to version control
        │
        ▼
  CI/CD runs: alembic upgrade head
  (before new app version is deployed)
        │
        ▼
  New app version deployed
  (with updated models that match the new schema)
```

### Migration Naming Convention

Migrations follow the pattern: `YYYY_MM_DD_description.py`

| Migration Name | Description |
|---|---|
| `2026_06_20_create_initial_tables.py` | Initial schema: users, events, registrations, attendance |
| `2026_07_15_add_event_cover_image.py` | Adding cover image URL to events |
| `2026_08_01_add_waitlist_position.py` | Adding waitlist position index to registrations |

The date prefix (`YYYY_MM_DD`) ensures chronological ordering. The short description after the underscore describes the purpose. If multiple migrations are created on the same day, append a letter: `2026_07_15_a_add_cover_image.py`, `2026_07_15_b_add_waitlist.py`.

### CI/CD Pipeline Integration

Migrations run as an explicit CI/CD step, never at application startup:

```yaml
# .github/workflows/deploy.yml (excerpt)
jobs:
  migrate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements.txt
      - run: alembic upgrade head
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}

  deploy:
    needs: [migrate]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: docker build -t app .
      - run: docker push app:latest
      - run: kubectl rollout restart deployment/app
```

This ordering guarantees:
- Migrations complete before traffic hits the new app version
- If a migration fails, the deployment is aborted and the old version continues serving
- Multiple instances never race to run migrations (there is only one migration job)

### Rollback Strategy

Alembic supports automatic rollbacks (downgrade):

```bash
# Rollback the last migration
alembic downgrade -1

# Rollback to a specific revision
alembic downgrade <revision_id>

# Preview the downgrade SQL
alembic downgrade --sql <revision_id>
```

**Critical rules for rollbacks:**
- Never edit an existing migration file — this would change its revision ID and break reproducibility.
- Always test the downgrade in a staging environment before applying to production.
- If the migration dropped columns or tables, the downgrade may cause data loss. Ensure backups exist before rolling back destructive migrations.
- For column drops: create the rollback migration as a new forward migration that re-adds the column, rather than reverting history. This preserves audit trail and avoids revision ID mismatches.

### Protected Migration Rules

| Rule | Rationale |
|---|---|
| Never edit migration files after creation | Alembic uses a revision ID to track migration order. Editing a committed migration changes its state, causing `alembic upgrade head` to fail with a "Target database is not up to date" error. |
| Always review auto-generated Python migrations | Alembic generates safe defaults, but it may produce `op.drop_column()` or `op.drop_table()` when renaming models. Always verify the generated migration before committing. |
| One migration per schema change | Grouping unrelated changes into a single migration makes rollbacks complex. If a rollback is needed, you may have to revert changes you wanted to keep. |
| Test migrations against a copy of production | Use `pg_dump` to create an anonymous copy of the production database, restore it locally, and run the migration to verify it completes within acceptable downtime. |

---

## 7. Seed Data

### Seed Script: `scripts/seed.py`

```python
import asyncio
import uuid

from sqlalchemy import text
from app.core.database import async_session
from app.core.security import get_password_hash
from app.models.user import User, Role, UserStatus
from app.models.event import Event, EventType, EventCategory, EventStatus
from app.models.registration import Registration, RegistrationRole, RegistrationStatus
from app.models.attendance import Attendance, AttendanceStatus
from datetime import datetime, timedelta, timezone


async def seed() -> None:
    async with async_session() as session:
        # ── Cleanup existing data ──────────────────────
        # Delete in reverse dependency order to respect foreign key constraints
        await session.execute(text("DELETE FROM attendance"))
        await session.execute(text("DELETE FROM registrations"))
        await session.execute(text("DELETE FROM events"))
        await session.execute(text("DELETE FROM users"))
        await session.commit()

        # ── Password hashing ───────────────────────────
        admin_password = get_password_hash("Admin@123")
        teacher_password = get_password_hash("Teacher@123")
        student_password = get_password_hash("Student@123")

        # ── Admin ──────────────────────────────────────
        admin = User(
            name="System Administrator",
            email="admin@college.edu",
            password_hash=admin_password,
            role=Role.ADMIN,
            status=UserStatus.ACTIVE,
        )
        session.add(admin)
        await session.flush()
        print(f"  ✓ Admin created: {admin.email}")

        # ── Teachers ───────────────────────────────────
        active_teacher = User(
            name="Dr. Rajesh Kumar",
            email="rajesh.kumar@college.edu",
            password_hash=teacher_password,
            role=Role.TEACHER,
            status=UserStatus.ACTIVE,
        )
        session.add(active_teacher)
        await session.flush()

        pending_teacher = User(
            name="Prof. Sunita Sharma",
            email="sunita.sharma@college.edu",
            password_hash=teacher_password,
            role=Role.TEACHER,
            status=UserStatus.PENDING,
        )
        session.add(pending_teacher)
        await session.flush()

        rejected_teacher = User(
            name="Dr. Amit Patel",
            email="amit.patel@college.edu",
            password_hash=teacher_password,
            role=Role.TEACHER,
            status=UserStatus.REJECTED,
        )
        session.add(rejected_teacher)
        await session.flush()
        print("  ✓ Teachers created: 1 active, 1 pending, 1 rejected")

        # ── Students ───────────────────────────────────
        student1 = User(
            name="Priya Singh",
            email="priya.singh@college.edu",
            password_hash=student_password,
            role=Role.STUDENT,
            status=UserStatus.ACTIVE,
        )
        session.add(student1)
        await session.flush()

        student2 = User(
            name="Arjun Nair",
            email="arjun.nair@college.edu",
            password_hash=student_password,
            role=Role.STUDENT,
            status=UserStatus.ACTIVE,
        )
        session.add(student2)
        await session.flush()

        student3 = User(
            name="Neha Gupta",
            email="neha.gupta@college.edu",
            password_hash=student_password,
            role=Role.STUDENT,
            status=UserStatus.ACTIVE,
        )
        session.add(student3)
        await session.flush()

        pending_student = User(
            name="Rohan Desai",
            email="rohan.desai@college.edu",
            password_hash=student_password,
            role=Role.STUDENT,
            status=UserStatus.PENDING,
        )
        session.add(pending_student)
        await session.flush()
        print("  ✓ Students created: 3 active, 1 pending")

        # ── Events ─────────────────────────────────────
        future_date = datetime.now(timezone.utc) + timedelta(days=14)

        past_date = datetime.now(timezone.utc) - timedelta(days=7)

        next_week_start = datetime.now(timezone.utc) + timedelta(days=7)
        next_week_end = datetime.now(timezone.utc) + timedelta(days=8)

        # In-College Approved Event (created by admin, coordinated by active teacher)
        event1 = Event(
            title="Annual Tech Fest 2026",
            description="A two-day technology festival featuring coding competitions, "
                        "robotics workshops, and guest lectures from industry "
                        "professionals. Open to all college students.",
            type=EventType.IN_COLLEGE,
            category=EventCategory.BOTH,
            status=EventStatus.APPROVED,
            venue="Main Auditorium & CS Block",
            start_date=future_date,
            end_date=future_date + timedelta(days=1),
            max_registrations=200,
            created_by_id=admin.id,
            coordinator_id=active_teacher.id,
        )
        session.add(event1)
        await session.flush()

        # In-College Approved Event (created by teacher, smaller scale)
        event2 = Event(
            title="Debate Competition: Current Affairs",
            description="Inter-department debate competition on current affairs "
                        "topics. Teams of 2 participants each. Topics will be "
                        "announced 30 minutes before each round.",
            type=EventType.IN_COLLEGE,
            category=EventCategory.PARTICIPANT,
            status=EventStatus.APPROVED,
            venue="Seminar Hall, 3rd Floor",
            start_date=next_week_start,
            end_date=next_week_end,
            max_registrations=32,
            created_by_id=active_teacher.id,
            coordinator_id=active_teacher.id,
        )
        session.add(event2)
        await session.flush()

        # Out-College Pending Event (requires admin approval)
        event3 = Event(
            title="National Hackathon: CodeForCause",
            description="Inter-college national hackathon hosted at our campus. "
                        "Teams from 15+ colleges expected. Prize pool of "
                        "₹1,00,000. 24-hour coding marathon.",
            type=EventType.OUT_COLLEGE,
            category=EventCategory.PARTICIPANT,
            status=EventStatus.PENDING,
            venue="Whole Campus",
            start_date=future_date + timedelta(days=30),
            end_date=future_date + timedelta(days=32),
            max_registrations=500,
            created_by_id=active_teacher.id,
            coordinator_id=active_teacher.id,
        )
        session.add(event3)
        await session.flush()

        # Past Event (for attendance testing)
        event4 = Event(
            title="Freshers Welcome 2026",
            description="Welcome ceremony for the batch of 2026. Cultural "
                        "performances, games, and refreshments.",
            type=EventType.IN_COLLEGE,
            category=EventCategory.PARTICIPANT,
            status=EventStatus.APPROVED,
            venue="College Ground",
            start_date=past_date,
            end_date=past_date,
            max_registrations=500,
            created_by_id=admin.id,
            coordinator_id=active_teacher.id,
        )
        session.add(event4)
        await session.flush()
        print("  ✓ Events created: 2 approved (in-college), 1 pending (out-college), 1 past")

        # ── Registrations ──────────────────────────────
        # Student 1 → Event 1 (participant) — accepted
        session.add(Registration(
            event_id=event1.id,
            student_id=student1.id,
            role_type=RegistrationRole.PARTICIPANT,
            status=RegistrationStatus.ACCEPTED,
        ))

        # Student 1 → Event 1 (volunteer) — accepted (dual role)
        session.add(Registration(
            event_id=event1.id,
            student_id=student1.id,
            role_type=RegistrationRole.VOLUNTEER,
            status=RegistrationStatus.ACCEPTED,
        ))

        # Student 2 → Event 1 (participant) — pending
        session.add(Registration(
            event_id=event1.id,
            student_id=student2.id,
            role_type=RegistrationRole.PARTICIPANT,
            status=RegistrationStatus.PENDING,
        ))

        # Student 3 → Event 2 (participant) — accepted
        session.add(Registration(
            event_id=event2.id,
            student_id=student3.id,
            role_type=RegistrationRole.PARTICIPANT,
            status=RegistrationStatus.ACCEPTED,
        ))

        # Student 1 → Event 3 (participant) — pending (out-college, waiting for event approval)
        session.add(Registration(
            event_id=event3.id,
            student_id=student1.id,
            role_type=RegistrationRole.PARTICIPANT,
            status=RegistrationStatus.PENDING,
        ))

        # Student 2, 3 → Event 4 (participant) — accepted (past event, for attendance testing)
        session.add(Registration(
            event_id=event4.id,
            student_id=student2.id,
            role_type=RegistrationRole.PARTICIPANT,
            status=RegistrationStatus.ACCEPTED,
        ))

        session.add(Registration(
            event_id=event4.id,
            student_id=student3.id,
            role_type=RegistrationRole.PARTICIPANT,
            status=RegistrationStatus.ACCEPTED,
        ))

        await session.flush()
        print("  ✓ Registrations created: 7 entries across all events")

        # ── Attendance ─────────────────────────────────
        # Past event attendance (Event 4)
        session.add(Attendance(
            event_id=event4.id,
            student_id=student2.id,
            marked_by_id=active_teacher.id,
            date=past_date.date(),
            status=AttendanceStatus.PRESENT,
        ))

        session.add(Attendance(
            event_id=event4.id,
            student_id=student3.id,
            marked_by_id=active_teacher.id,
            date=past_date.date(),
            status=AttendanceStatus.ABSENT,
        ))

        await session.flush()
        print("  ✓ Attendance records created: 2 entries")

        await session.commit()

    print("\n✓ Seed completed successfully!")
    print("  Admin:     admin@college.edu / Admin@123")
    print("  Teacher:   rajesh.kumar@college.edu / Teacher@123")
    print("  Student:   priya.singh@college.edu / Student@123")


if __name__ == "__main__":
    asyncio.run(seed())
```

### Password Security: `app/core/security.py`

```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)
```

### Run the Seed

```bash
python scripts/seed.py
```

### Seed Data Summary

| Entity | Count | Details |
|---|---|---|
| Admin | 1 | `admin@college.edu` — super admin account with full access |
| Teachers | 3 | 1 active (`rajesh.kumar@college.edu`), 1 pending, 1 rejected |
| Students | 4 | 3 active (`priya.singh@college.edu`, `arjun.nair@college.edu`, `neha.gupta@college.edu`), 1 pending |
| Events | 4 | 2 approved in-college, 1 pending out-college, 1 past event |
| Registrations | 7 | Dual-role registration (student 1 for event 1 as both participant and volunteer), mix of accepted and pending |
| Attendance | 2 | 1 present, 1 absent — both for the past event |

---

## 8. Connection Pool Configuration

### Engine Configuration

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

engine = create_async_engine(
    "postgresql+asyncpg://user:password@host:5432/acharya",
    pool_size=15,
    max_overflow=5,
    pool_timeout=30,
    pool_pre_ping=True,
    echo=False,
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
```

### Connection URL Format

```
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/acharya
```

### Pool Sizing Formula

```
connections = (core_count × 2) + effective_spindle_count
```

Where:
- `core_count`: Number of CPU cores available to the application
- `effective_spindle_count`: Number of physical disks (or SSDs) — for cloud VMs with SSDs, use 1

**Example calculations:**

| Deployment | Cores | Spindles | Calculated Pool | pool_size | max_overflow |
|---|---|---|---|---|---|
| Development (laptop) | 4 | 1 | (4 × 2) + 1 = 9 | 10 | 2 |
| Staging (2 CPU, 4 GB) | 2 | 1 | (2 × 2) + 1 = 5 | 10 | 2 |
| Production (4 CPU, 8 GB) | 4 | 1 | (4 × 2) + 1 = 9 | 15 | 5 |
| Production (8 CPU, 16 GB) | 8 | 1 | (8 × 2) + 1 = 17 | 20 | 5 |

**Important:** Each connection counts against the PostgreSQL `max_connections` setting. The total across all application instances must not exceed `max_connections` minus reserved connections for superuser access and monitoring tools.

### Production Guidelines

1. **Start with 10-20 connections** in the pool for a single application instance. Monitor `pg_stat_activity` to see actual usage. Adjust based on:
   - Average query duration (longer queries → need more connections)
   - Request throughput (higher RPS → need more connections)
   - Number of concurrent application instances

2. **Monitor with `pg_stat_activity`:**
   ```sql
   SELECT state, count(*) FROM pg_stat_activity WHERE datname = 'acharya' GROUP BY state;
   SELECT * FROM pg_stat_activity WHERE datname = 'acharya' AND state = 'active';
   ```
   Key metrics: `active`, `idle`, `idle in transaction` connections.

3. **Set `pool_timeout` to 30 seconds** — if a connection cannot be acquired within 30 seconds, the request fails fast rather than hanging indefinitely.

4. **Use PgBouncer for transaction pooling** when scaling beyond 500 concurrent users:
   ```ini
   [pgbouncer]
   pool_mode = transaction
   max_client_conn = 500
   default_pool_size = 20
   reserve_pool_size = 5
   reserve_pool_timeout = 5
   ```
   Transaction pooling means connections are released back to the pool after each transaction (not after each client connection), allowing many clients to share few database connections.

### Connection Pool Best Practices

| Practice | Why |
|---|---|
| Pool size should be close to (not exceed) the number of concurrent workers | Each connection consumes ~10 MB of RAM in PostgreSQL. Over-provisioning wastes memory. Under-provisioning causes request queuing. |
| Always set `pool_timeout` | Without a timeout, stalled connection acquisition requests accumulate, eventually exhausting the asyncio event loop. |
| Use `engine.dispose()` in graceful shutdown | Drain active queries and close connections cleanly before process exit. Prevents connection leaks. |
| Enable `pool_pre_ping=True` | Verifies the connection is alive before handing it to the application. Prevents errors from stale connections after a database restart. |
| Monitor with `pg_stat_activity` | Run `SELECT * FROM pg_stat_activity WHERE datname = 'acharya'` to see active queries and idle connections. Look for "idle in transaction" connections — these hold locks and block other queries. |
| Do not set `pool_size=0` | Value 0 means unlimited — this can exhaust PostgreSQL's `max_connections` and crash the database. |

---

## 9. Naming Conventions

### Table Naming

| Convention | Rule | Examples |
|---|---|---|
| Format | `snake_case`, plural | `users`, `events`, `registrations`, `attendance` |
| Rule | Use the plural form of the entity name | `registration` → `registrations`, `user` → `users` |
| Exception | Mass nouns (uncountable) use singular | `attendance` (not `attendances`) |
| Join tables | `table1_table2` in alphabetical order | Not applicable in this schema (no many-to-many relationships yet) |
| SQLAlchemy `__tablename__` | All models use `__tablename__ = "snake_case_plural"` | Model `User` → `__tablename__ = "users"` |

### Column Naming

| Convention | Rule | Examples |
|---|---|---|
| Format | `snake_case` | `password_hash`, `created_at`, `start_date` |
| Primary keys | Always `id` (singular, no prefix) | `id`, not `user_id` (the table name qualifies it) |
| Foreign keys | `singular_table_name_id` | `event_id`, `student_id`, `marked_by_id` |
| Foreign keys (verb prefix) | Use past tense verbs | `created_by_id`, `marked_by_id` |
| Timestamps | `{action}_at` | `created_at`, `updated_at`, `registered_at`, `marked_at` |
| Boolean flags | Use positive `is_` or `has_` prefix | (Not used yet but available: `is_active`, `has_consent`) |
| JSON columns | Suffix with `_data` or `_meta` | (Not used yet: `event_meta`, `preferences_data`) |

### Enum Naming

| Convention | Rule | Examples |
|---|---|---|
| Format | PascalCase (Python enum), snake_case (DB value) | `Role.STUDENT` → `"student"` |
| Enum class name | Singular noun | `Role` not `Roles`, `EventType` not `EventTypes` |
| Enum values | UPPER_CASE (Python), snake_case (DB) | `Role.ADMIN` → `"admin"` |
| DB values are lowercase | Always store lowercase | `"approved"` not `"APPROVED"` or `"Approved"` |

### Index Naming

| Convention | Rule | Examples |
|---|---|---|
| Format | `ix_table_column1_column2` | `ix_users_role_status` |
| Unique constraints | `uq_table_col1_col2` | `uq_registrations_event_student_role` |
| Primary key | Always named by PostgreSQL default: `{tablename}_pkey` | `users_pkey` |
| Rule | Omit redundant column qualifiers | `users_email_idx` not `users_users_email_idx` |
| Rule | Columns in same order as index definition | `ix_events_status_type` → index on `(status, type)` |

### Foreign Key Naming

PostgreSQL auto-generates foreign key constraint names with the pattern `{tablename}_{fk_column}_fkey` (e.g., `registrations_event_id_fkey`). These are not explicitly named in the schema to avoid clutter, but they follow a predictable pattern for debugging:

```sql
SELECT conname FROM pg_constraint WHERE conrelid = 'registrations'::regclass;
-- Returns: registrations_event_id_fkey, registrations_student_id_fkey
```

### Complete Naming Reference

| Category | Pattern | Example in SQLAlchemy | Example in PostgreSQL |
|---|---|---|---|
| Model | PascalCase singular, `__tablename__` snake_case plural | `class User(Base): __tablename__ = "users"` | `users` |
| Column | snake_case | `password_hash = mapped_column(Text)` | `password_hash` |
| Enum class | PascalCase | `class Role(str, enum.Enum):` | — |
| Enum value | UPPER_CASE → snake_case in DB | `Role.ADMIN` | `"admin"` |
| Index | `ix_table_column1_column2` | `Index("ix_users_role_status", "role", "status")` | `ix_users_role_status` |
| Unique | `uq_table_col1_col2` | `UniqueConstraint(..., name="uq_registrations_event_student_role")` | `uq_registrations_event_student_role` |
| Primary key | `{table}_pkey` (auto) | — | `users_pkey` |
| Foreign key | `{table}_{column}_fkey` (auto) | — | `registrations_event_id_fkey` |

---

## Appendix: Migration Diff Commands

### Before Deploying to Production

```bash
# Check what migrations are pending
alembic current

# Preview the SQL that will be executed
alembic upgrade --sql head

# Apply migrations
alembic upgrade head
```

### Manual Rollback

```bash
# Generate rollback SQL (current -> previous)
alembic downgrade --sql <previous_revision_id> > rollback_20260715.sql

# Review and execute
psql "$DATABASE_URL" -f rollback_20260715.sql

# Mark the migration as not applied
# (Alembic tracks applied migrations in the alembic_version table)
psql "$DATABASE_URL" -c "DELETE FROM alembic_version WHERE version_num = '<revision_id>';"

# Delete migration file
rm alembic/versions/2026_07_15_add_event_cover_image.py
```

### Reset Local Database

```bash
# Drop all tables and re-apply all migrations
alembic downgrade base
alembic upgrade head

# Or: drop and recreate with seed
psql -c "DROP DATABASE acharya;" && psql -c "CREATE DATABASE acharya;"
alembic upgrade head
python scripts/seed.py
```
