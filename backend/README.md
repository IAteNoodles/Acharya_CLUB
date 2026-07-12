# Acharya_CLUB

College Event Management System — REST API built with [FastAPI](https://fastapi.tiangolo.com/).

Manage events, registrations, attendance, and in-app notifications with role-based access for students, teachers, and admins.

## Features

- **Role-based access** — Students, teachers, and admins with granular permissions per endpoint.
- **Event lifecycle** — Admins create in-college events, students create out-college events. Teachers can only act as coordinators (approving events and marking attendance), they do not create events.
- **Registration system** — Students register as volunteers or participants; coordinators accept or reject.
- **Attendance tracking** — Bulk mark attendance per event/date with present/absent/late status.
- **Notification system** — In-app notifications for registration acceptance/rejection, event approval/rejection, and teacher approval/rejection.
- **Dashboard & reports** — Aggregate stats on users, events, registrations, attendance, and notifications.
- **Rate limiting** — Sliding-window rate limiter (general 100 req/min, auth 20 req/min) with Redis or in-memory fallback.
- **JWT authentication** — Access + refresh token pair with blacklist revocation on logout.
- **Security middleware** — CSP, HSTS, X-Frame-Options, X-Content-Type-Options, and request timeout.
- **Structured logging** — [structlog](https://www.structlog.org/) with request IDs for traceability.

## Architecture

```
┌──────────────┐     ┌─────────────────────────┐     ┌──────────────┐
│   Frontend   │────▶│  FastAPI (uvicorn)       │────▶│  PostgreSQL  │
│  (React SPA) │     │  app/                    │     │  (Supabase)  │
└──────────────┘     │  ├── api/v1/   (routes)  │     └──────────────┘
                     │  ├── services/ (logic)   │     ┌──────────────┐
                     │  ├── models/   (ORM)     │────▶│  Redis       │
                     │  ├── schemas/  (Pydantic)│     │  (Upstash)   │
                     │  ├── middleware/         │     └──────────────┘
                     │  └── core/     (config)  │
                     └─────────────────────────┘
```

The API follows a layered pattern: **routes → services → models**. Middleware handles rate limiting, security headers, request timeouts, and request-ID injection. Database migrations use Alembic.

## Prerequisites

- Python 3.12+
- PostgreSQL 16+ (or a Supabase project)
- Redis 7+ (optional, falls back to in-memory)

## Getting started

### 1. Clone and install

```bash
git clone <repo-url>
cd Acharya_CLUB

python -m venv .venv
.venv\Scripts\activate     # Windows
source .venv/bin/activate  # macOS/Linux

cd backend
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and set your Supabase database password and a strong `JWT_SECRET` (or leave `JWT_SECRET` unset — a development secret is auto-generated):

```bash
# Generate a production JWT secret:
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

For the database you can either set `DATABASE_URL` directly or use the component fields (requires `DB_PASSWORD`):

```
DATABASE_URL=postgresql+asyncpg://postgres.qwouxrnnwmkotkwraqme:YOUR_PASSWORD@aws-1-ap-northeast-1.pooler.supabase.com:5432/postgres?ssl=require
```

> [!TIP]
> In production, set `DB_PASSWORD` via environment variable (not `.env`) and omit `DATABASE_URL`. The app constructs the full URL automatically.

### 3. Run database migrations

```bash
alembic upgrade head
```

### 4. Start the server

```bash
uvicorn app.main:create_app --factory --reload --port 8000
```

The API is available at `http://localhost:8000/api/v1`, with interactive docs at `/api/v1/docs`.

### 5. Run with Docker

```bash
# Development (with hot-reload)
docker compose up

# Production
docker compose -f docker-compose.prod.yml up

# Optional local Postgres + Redis (for offline dev without Supabase):
# docker compose --profile local-db up
```

## Configuration

Key environment variables (see `.env.example` for defaults):

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL async connection string |
| `DB_PASSWORD` | Supabase password (alternative to DATABASE_URL) |
| `JWT_SECRET` | Signing key for tokens (min 32 chars) |
| `JWT_ACCESS_EXPIRE_MINUTES` | Access token TTL (default 15) |
| `JWT_REFRESH_EXPIRE_DAYS` | Refresh token TTL (default 7) |
| `REDIS_URL` | Redis connection string |
| `UPSTASH_REDIS_REST_URL` | Upstash Redis URL (overrides REDIS_URL) |
| `UPSTASH_REDIS_REST_TOKEN` | Upstash Redis token |
| `CORS_ORIGINS` | JSON array of allowed origins |
| `REQUEST_TIMEOUT_SECONDS` | Request timeout (default 30) |

## API endpoints

The API prefix is `/api/v1`.

| Group | Endpoints | Auth | Description |
|---|---|---|---|
| `health` | `GET /health` | No | Health check |
| `auth` | `POST /signup`, `/login`, `/refresh`, `/logout`, `GET /me` | Mixed | Authentication |
| `events` | `GET`, `POST`, `GET /{id}`, `PUT /{id}`, `POST /{id}/approve`, `POST /{id}/reject`, `POST /{id}/assign-coordinator` | JWT | Event CRUD and moderation |
| `registrations` | `POST /`, `GET /my`, `GET /event/{id}`, `PATCH /{id}/accept`, `PATCH /{id}/reject` | JWT | Registration management |
| `attendance` | `POST /bulk`, `GET /event/{id}`, `GET /my` | JWT | Attendance tracking |
| `notifications` | `GET /`, `PATCH /{id}/read`, `POST /read-all` | JWT | In-app notifications |
| `reports` | `GET /dashboard` | JWT | Dashboard statistics |
| `users` | `GET /me`, `PATCH /me`, `GET /`, `PATCH /{id}/status` | JWT | User management |

## Testing

```bash
# Unit and integration tests (default)
pytest

# Exclude slow tests
pytest -m "not slow"

# End-to-end tests (requires Docker)
pytest -m e2e

# With coverage
pytest --cov=app --cov-report=term-missing
```

The test suite covers **97%** of the codebase with 333 tests. Mocking strategy uses `AsyncMock` for async database sessions and `MagicMock` for SQLAlchemy models.

> [!NOTE]
> Tests in `tests/real_db/` run against the database configured via `DATABASE_URL` or `DB_PASSWORD` in `.env`. These are **not skipped** — they will error if the database is unreachable. See `.env.example` for Supabase configuration.

## Project structure

```
backend/
├── alembic/              # Database migrations
│   └── versions/         # 0001_initial_schema, 0002_notifications
├── app/
│   ├── api/
│   │   ├── deps.py       # Auth dependencies (get_current_user, require_admin, etc.)
│   │   └── v1/           # Route handlers
│   ├── core/
│   │   ├── config.py     # Pydantic Settings with validators
│   │   ├── database.py   # Async SQLAlchemy engine and session factory
│   │   ├── exceptions.py # Custom exception classes + handlers
│   │   ├── redis.py      # Redis/Upstash client singleton
│   │   └── security.py   # JWT and bcrypt helpers
│   ├── middleware/
│   │   ├── rate_limit.py # Sliding-window rate limiter
│   │   ├── security.py   # CSP, HSTS, X-Frame-Options headers
│   │   └── timeout.py    # Request timeout middleware
│   ├── models/           # SQLAlchemy ORM models
│   ├── schemas/          # Pydantic request/response schemas
│   └── services/         # Business logic layer
├── scripts/              # Docker entrypoint, helpers
└── tests/                # pytest suite
```

## Tech stack

| Layer | Technology |
|---|---|
| Runtime | Python 3.13 |
| Framework | FastAPI 0.138 |
| ASGI server | uvicorn 0.34 |
| ORM | SQLAlchemy 2.0 (async) |
| Database | PostgreSQL 16 (asyncpg) |
| Migrations | Alembic |
| Auth | PyJWT + bcrypt |
| Cache/Rate limit | Redis 7 (redis-py), Upstash REST, or in-memory fallback |
| Validation | Pydantic v2 + Pydantic Settings |
| Logging | structlog |
| Testing | pytest, pytest-asyncio, httpx, fakeredis, testcontainers |

## Security

- All endpoints except health check require JWT Bearer authentication.
- Tokens use HS256 with configurable TTL; refresh tokens are rotated and blacklisted on logout.
- CORS restricted to configured origins.
- Security headers enforced: CSP, HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy.
- Rate limiting on all endpoints (100 req/min) with stricter limits on auth endpoints (20 req/min).
- Request timeout defaults to 30 seconds.
