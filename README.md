# Acharya_CLUB — College Event Management System

[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.138+-00a86b)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791)](https://postgresql.org)
[![Docker](https://img.shields.io/badge/Docker-Multi--stage-2496ED)](https://docker.com)
[![CI](https://img.shields.io/badge/CI-GitHub%20Actions-2088FF)](.github/workflows/ci.yml)

A production-grade REST API that digitises the full lifecycle of college events — from proposal and approval through registration, attendance tracking, in-app notifications, and reporting. Built as a modular monolith with a 3-role RBAC hierarchy (Student / Teacher / Admin) and designed for single-college deployments.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Runtime | Python 3.13 |
| Web Framework | FastAPI 0.138+ |
| ASGI Server | Uvicorn 0.34 |
| ORM | SQLAlchemy 2.0 (async via asyncpg) |
| Database | PostgreSQL 16 (Supabase) |
| Cache / Rate Limiting | Redis / Upstash Redis |
| Auth | PyJWT (HS256) + bcrypt |
| Migrations | Alembic |
| Validation | Pydantic v2 / pydantic-settings |
| Logging | structlog (structured JSON) |
| Containerisation | Docker multi-stage (Alpine-based) |
| CI/CD | GitHub Actions |
| Testing | pytest 9.1+, pytest-asyncio, httpx, fakeredis, testcontainers |

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
- **Async-first** — FastAPI + asyncpg + SQLAlchemy 2.0 async sessions throughout
- **3-role RBAC** — Student (browse/register), Teacher (coordinate/mark), Admin (full control)
- **JWT with rotation** — 15-min access tokens, 7-day refresh tokens with rotation
- **In-app notifications** — 6 notification types auto-created on state changes
- **Structured logging** — structlog outputs ISO-timestamped JSON
- **Redis rate limiting** — sliding-window via Redis sorted sets, with in-memory fallback

---

## Getting Started

### One command, any laptop (Docker)

The repo-root `docker-compose.yml` runs the entire stack — PostgreSQL, Redis,
migrations, demo-data seeding, the FastAPI backend, and the React frontend —
with no other prerequisites than Docker:

```bash
docker compose up --build
```

Then open **http://localhost:3000** (frontend; nginx proxies `/api/v1` to the
backend) or **http://localhost:8000/api/v1/docs** (interactive API docs).
Demo logins: `admin@college.edu`/`Admin@123`, `rajesh.kumar@college.edu`/`Teacher@123`,
`priya.singh@college.edu`/`Student@123`.

Data persists in the `pgdata` volume; the seed runs only when the database is
empty. `docker compose down -v` resets everything. If a port is taken on your
machine, override it: `FRONTEND_PORT=3001 BACKEND_PORT=8001 docker compose up`.

### Prerequisites

- Python 3.12+
- PostgreSQL 16 (or Docker)
- Redis 7 (optional, for production rate limiting)

### Local Development

```bash
# Clone and enter the project
git clone <repo-url>
cd Acharya_CLUB/backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate    # Linux/Mac
.venv\Scripts\activate       # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your DB credentials and a strong JWT_SECRET

# Run migrations
alembic upgrade head

# Seed sample data (optional)
python scripts/seed.py

# Start the server
uvicorn app.main:create_app --factory --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000/api/v1`. Interactive docs at `http://localhost:8000/api/v1/docs`.

### Docker Development

```bash
# Start all services with local Postgres and Redis
docker compose --profile local-db up

# Start app only (expects external Postgres/Redis)
docker compose up
```

### Production Deployment

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

---

## Project Structure

```
Acharya_CLUB/
├── .github/workflows/ci.yml        # CI pipeline
├── docs/                            # Design documents & specs
│   ├── architecture.md
│   ├── api-specification.md
│   ├── database-schema.md
│   └── redis-plan.md
└── backend/
    ├── .env.example                 # Environment template
    ├── requirements.txt             # Pinned dependencies
    ├── pyproject.toml               # Project metadata & pytest config
    ├── Dockerfile                   # Multi-stage build
    ├── docker-compose.yml           # Dev stack
    ├── docker-compose.prod.yml      # Production overrides
    ├── alembic.ini / alembic/       # Database migrations
    ├── scripts/
    │   ├── seed.py                  # Data seeder
    │   └── entrypoint.sh            # Docker entrypoint
    ├── app/
    │   ├── main.py                  # FastAPI app factory (create_app)
    │   ├── core/                    # Infrastructure
    │   │   ├── config.py            # pydantic-settings
    │   │   ├── database.py          # Async engine + session
    │   │   ├── security.py          # JWT + bcrypt
    │   │   ├── redis.py             # Redis singleton
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
        ├── test_e2e_workflows.py    # Full E2E tests
        └── real_db/                 # Real PostgreSQL tests
            ├── conftest.py
            └── test_*.py            # 7 real DB test files
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
- **Attendance** — event + student + date, status (present/absent/late), unique per (event, student, date)
- **Notification** — user, type (6 types), title, message, related entity, is_read

---

## Testing

Three-layer testing strategy with 29 test files:

| Layer | Approach | Dependencies | Speed |
|---|---|---|---|
| **Unit / Mock** | `AsyncMock`, `dependency_overrides`, `httpx.AsyncClient`+`ASGITransport` | None | Fast (~1-2s) |
| **Real DB** | `testcontainers.PostgresContainer`, rollback-per-test | Docker (Postgres) | Moderate (~5-10s) |
| **E2E** | `PostgresContainer` + `RedisContainer`, full lifecycle | Docker (both) | Slow (~20-30s) |

```bash
# Default: unit + real DB tests (excludes E2E)
pytest -v

# Unit/mock tests only
pytest -v -m "not real_db and not e2e"

# Real DB tests only
pytest -v tests/real_db/

# All tests including E2E
pytest -v -m ""

# With coverage
pytest --cov=app --cov-report=term-missing
```

---

## Configuration

All configuration via environment variables (or `.env` file) using pydantic-settings. See `backend/.env.example` for all options.

### Required

| Variable | Description |
|---|---|
| `JWT_SECRET` | HMAC key for JWT (min 32 characters) |
| `DB_PASSWORD` | Database password (or set `DATABASE_URL` directly) |

### Key Optional

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | computed | Full asyncpg connection string |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis URL |
| `JWT_ACCESS_EXPIRE_MINUTES` | 15 | Access token lifetime |
| `JWT_REFRESH_EXPIRE_DAYS` | 7 | Refresh token lifetime |
| `CORS_ORIGINS` | localhost:5173,8000 | Allowed CORS origins |
| `LOG_LEVEL` | INFO | Log level |
| `REQUEST_TIMEOUT_SECONDS` | 30 | Request timeout |
| `DATABASE_POOL_SIZE` | 5 | Connection pool size |

---

## Docker

Multi-stage Dockerfile (Alpine-based):

| Stage | Base | Purpose |
|---|---|---|
| `builder` | `python:3.13-alpine` | Compile dependencies |
| `development` | From builder | Hot-reload with volume mount, health check |
| `production` | From builder | Stripped runtime, auto-migrations, non-root user |

Entrypoint auto-runs `alembic upgrade head` before starting the server.

Full-stack orchestration lives in the **repo-root** `docker-compose.yml`
(db + redis + backend + frontend, seed-if-empty). The compose files inside
`backend/` remain for backend-only workflows (hot-reload dev, prod overrides).

---

## License

MIT
