# Acharya_CLUB — College Event Management System

A production-grade REST API that digitises the full lifecycle of college events — from proposal and approval through registration, attendance tracking, in-app notifications, and reporting. Built as a modular monolith with a 3-role RBAC hierarchy (Student / Teacher / Admin) and designed for single-college deployments.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Runtime | Python 3.12+ |
| Web Framework | FastAPI 0.138+ |
| ASGI Server | Uvicorn 0.34 |
| ORM | SQLAlchemy 2.0 (async via aiosqlite) |
| Database | SQLite |
| Auth | PyJWT (HS256) + bcrypt |
| Validation | Pydantic v2 / pydantic-settings |
| Logging | structlog (structured JSON) |
| Testing | pytest 9.1+, pytest-asyncio, httpx |

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      FastAPI App                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐ │
│  │ Middleware │  │  Router  │  │  Service  │  │  Model │ │
│  │ (4 layers) │  │ (8 files)│  │ (7 files) │  │(5 files)│
│  └──────────┘  └──────────┘  └──────────┘  └────────┘ │
│        │              │              │              │    │
│  ┌─────┴──────┐  ┌────┴─────┐  ┌────┴────┐  ┌────┴───┐ │
│  │ Rate Limit │  │  Auth    │  │  Core    │  │  DB    │ │
│  │ Timeout    │  │  Deps    │  │ Config   │  │        │ │
│  │ Security   │  │          │  │ Security │  │        │ │
│  │ CORS       │  │          │  │ Exceptions│  │        │ │
│  └────────────┘  └──────────┘  └─────────┘  └────────┘ │
└─────────────────────────────────────────────────────────┘
```

- **Modular monolith** — cleanly separated layers for future extraction if needed
- **Async-first** — FastAPI + aiosqlite + SQLAlchemy 2.0 async sessions throughout
- **3-role RBAC** — Student (browse/register, create out-college events), Teacher (coordinate/mark, approve out-college events), Admin (full control, create in-college events)
- **JWT with rotation** — 15-min access tokens, 7-day refresh tokens with rotation
- **In-app notifications** — 6 notification types auto-created on state changes
- **Structured logging** — structlog outputs ISO-timestamped JSON

---

## Getting Started

### Prerequisites

- Python 3.12+

### Local Development

```bash
git clone <repo-url>
cd Acharya_CLUB/backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:create_app --factory --reload
```

No `.env` required (sane in-code defaults), no Docker, no external DB signup, no Redis, no CI. One file (`acharya_club.db`) holds all state. Tests run the same way, no containers.

The API will be available at `http://localhost:8000/api/v1`. Interactive docs at `http://localhost:8000/api/v1/docs`.

---

## Project Structure

```
Acharya_CLUB/
├── docs/                            # Design documents & specs
│   ├── architecture.md
│   ├── api-specification.md
│   └── database-schema.md
└── backend/
    ├── .env.example                 # Environment template
    ├── requirements.txt             # Pinned dependencies
    ├── pyproject.toml               # Project metadata & pytest config
    ├── scripts/
    │   └── seed.py                  # Data seeder
    ├── app/
    │   ├── main.py                  # FastAPI app factory (create_app)
    │   ├── core/                    # Infrastructure
    │   │   ├── config.py            # pydantic-settings
    │   │   ├── database.py          # Async engine + session
    │   │   ├── security.py          # JWT + bcrypt
    │   │   ├── exceptions.py        # AppHTTPException hierarchy
    │   │   └── logging_config.py    # structlog setup
    │   ├── models/                  # SQLAlchemy 2.0 models
    │   │   ├── base.py              # DeclarativeBase + TimestampMixin
    │   │   ├── user.py
    │   │   ├── event.py
    │   │   ├── registration.py
    │   │   ├── attendance.py
    │   │   └── notification.py
    │   ├── schemas/                 # Pydantic v2 schemas
    │   ├── services/                # Business logic
    │   └── api/
    │       ├── deps.py              # Auth dependencies
    │       └── v1/                  # Route handlers
    │           ├── auth.py
    │           ├── users.py
    │           ├── events.py
    │           ├── registrations.py
    │           ├── attendance.py
    │           ├── notifications.py
    │           ├── reports.py
    │           └── health.py
    └── tests/
        ├── conftest.py
        ├── test_*.py                # 21 unit/mock test files
        └── test_e2e_workflows.py    # Full E2E tests
```

---

## API Surface

All endpoints prefixed with `/api/v1`. Bearer JWT required except `health`, `auth/signup`, `auth/login`, `auth/refresh`.

### Auth
| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/health` | None | Health check |
| POST | `/auth/signup` | None | Register |
| POST | `/auth/login` | None | Login |
| POST | `/auth/refresh` | None | Rotate refresh token |
| POST | `/auth/logout` | Any | Blacklist tokens |
| GET | `/auth/me` | Any | Current user profile |

### Users
| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/users/pending-teachers` | Admin | List pending teachers |
| PATCH | `/users/{id}/approve` | Admin | Approve teacher |
| PATCH | `/users/{id}/reject` | Admin | Reject teacher |
| GET | `/users/teachers` | Admin | List active teachers |

### Events
| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/events` | Any | List events (filterable) |
| POST | `/events` | Any | Create event |
| GET | `/events/{id}` | Any | Get event |
| PATCH | `/events/{id}` | Creator/Admin | Update event |
| PATCH | `/events/{id}/approve` | Admin/Coordinator | Approve |
| PATCH | `/events/{id}/reject` | Admin/Coordinator | Reject |
| PATCH | `/events/{id}/assign-coordinator` | Admin | Assign coordinator |

### Registrations
| Method | Path | Role | Description |
|--------|------|------|-------------|
| POST | `/registrations` | Student | Register for event |
| GET | `/registrations/my` | Student | Own registrations |
| GET | `/registrations/event/{id}` | Teacher/Admin | Event registrations |
| PATCH | `/registrations/{id}/accept` | Teacher/Admin | Accept |
| PATCH | `/registrations/{id}/reject` | Teacher/Admin | Reject |

### Attendance
| Method | Path | Role | Description |
|--------|------|------|-------------|
| POST | `/attendance/bulk` | Teacher/Admin | Bulk upsert (1-100) |
| GET | `/attendance/event/{id}` | Teacher/Admin | Event attendance |
| GET | `/attendance/my` | Any | Own attendance |
| GET | `/attendance/student/{id}` | Admin | Student attendance |

### Notifications
| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/notifications` | Any | List (paginated) |
| GET | `/notifications/unread-count` | Any | Unread count |
| PATCH | `/notifications/{id}/read` | Any | Mark read |
| PATCH | `/notifications/read-all` | Any | Mark all read |

### Reports
| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/reports/dashboard` | Teacher/Admin | Dashboard (8 concurrent queries) |

---

## Database Schema

Five tables with UUID primary keys, automatic `created_at` / `updated_at` timestamps, and composite indexes on frequently filtered columns.

```
users 1──N events (created_by)
users 1──N events (coordinator)
users 1──N registrations (student)
users 1──N attendance (student)
users 1──N attendance (marked_by)
users 1──N notifications
events 1──N registrations
events 1──N attendance
```

### Key Models

- **User** — name, email (unique), password_hash, role (student/teacher/admin), status (pending/active/rejected)
- **Event** — title, description, event_type, category, status (draft/pending/approved/rejected), venue, dates, max_registrations
- **Registration** — event + student + role_type (volunteer/participant), status (pending/accepted/rejected), unique per (event, student, role_type)
- **Attendance** — event + student + date, status (present/absent), unique per (event, student, date)
- **Notification** — user, type (6 types), title, message, related entity, is_read

---

## Testing

Three-layer testing strategy with 29 test files:

| Layer | Approach | Dependencies | Speed |
|---|---|---|---|
| **Unit / Mock** | `AsyncMock`, `dependency_overrides`, `httpx.AsyncClient`+`ASGITransport` | None | Fast (~1-2s) |
| **Real DB** | `aiosqlite`, in-memory/temp files | None | Fast (~2-3s) |
| **E2E** | SQLite file db, full lifecycle | None | Moderate (~5-10s) |

```bash
# Run all tests
pytest -v

# With coverage
pytest --cov=app --cov-report=term-missing
```

---

## Configuration

All configuration via environment variables (or `.env` file) using pydantic-settings. See `backend/.env.example` for all options.

### Required

| Variable | Description |
|---|---|
| None | All variables have defaults |

### Key Optional

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite+aiosqlite:///./acharya_club.db` | Database string |
| `JWT_SECRET` | Auto-generated | HMAC key for JWT (min 32 chars) |
| `JWT_ACCESS_EXPIRE_MINUTES` | 15 | Access token lifetime |
| `JWT_REFRESH_EXPIRE_DAYS` | 7 | Refresh token lifetime |
| `CORS_ORIGINS` | localhost:5173,8000 | Allowed CORS origins |
| `LOG_LEVEL` | INFO | Log level |
| `REQUEST_TIMEOUT_SECONDS` | 30 | Request timeout |

---

## License

MIT
