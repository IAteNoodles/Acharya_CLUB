# Acharya_CLUB

College Event Management System — REST API built with [FastAPI](https://fastapi.tiangolo.com/).

Manage events, registrations, attendance, and in-app notifications with role-based access for students, teachers, and admins.

## Features

- **Role-based access** — Students, teachers, and admins with granular permissions per endpoint.
- **Event lifecycle** — Admins create in-college events, students create out-college events. Teachers can only act as coordinators (approving events and marking attendance), they do not create events.
- **Registration system** — Students register as volunteers or participants; coordinators accept or reject.
- **Attendance tracking** — Bulk mark attendance per event/date with present/absent status.
- **Notification system** — In-app notifications for registration acceptance/rejection, event approval/rejection, and teacher approval/rejection.
- **Dashboard & reports** — Aggregate stats on users, events, registrations, attendance, and notifications.
- **Rate limiting** — Sliding-window rate limiter (general 100 req/min, auth 20 req/min) with Redis or in-memory fallback.
- **JWT authentication** — Access + refresh token pair with blacklist revocation on logout.
- **Security middleware** — CSP, HSTS, X-Frame-Options, X-Content-Type-Options, and request timeout.
- **Structured logging** — [structlog](https://www.structlog.org/) with request IDs for traceability.

## Architecture

```
┌──────────────┐     ┌─────────────────────────┐     ┌──────────────┐
│   Frontend   │────▶│  FastAPI (uvicorn)      │────▶│  SQLite DB   │
│  (React SPA) │     │  app/                   │     │  (local file)│
└──────────────┘     │  ├── api/v1/   (routes) │     └──────────────┘
                     │  ├── services/ (logic)  │
                     │  ├── models/   (ORM)    │
                     │  ├── schemas/  (Pydantic)
                     │  ├── middleware/        │
                     │  └── core/     (config) │
                     └─────────────────────────┘
```

The API follows a layered pattern: **routes → services → models**. Middleware handles security headers, request timeouts, and request-ID injection. Database is created on startup automatically.

## Prerequisites

- Python 3.12+

## Getting started

```bash
git clone <repo-url>
cd Acharya_CLUB/backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:create_app --factory --reload
```

No `.env` required (sane in-code defaults), no Docker, no external DB signup, no Redis, no CI. One file (`acharya_club.db`) holds all state. Tests run the same way, no containers.

The API is available at `http://localhost:8000/api/v1`, with interactive docs at `/api/v1/docs`.

## Configuration

Key environment variables (see `.env.example` for defaults):

| Variable | Description |
|---|---|
| `DATABASE_URL` | SQLite async connection string |
| `JWT_SECRET` | Signing key for tokens (min 32 chars) |
| `JWT_ACCESS_EXPIRE_MINUTES` | Access token TTL (default 15) |
| `JWT_REFRESH_EXPIRE_DAYS` | Refresh token TTL (default 7) |
| `CORS_ORIGINS` | JSON array of allowed origins |
| `REQUEST_TIMEOUT_SECONDS` | Request timeout (default 30) |

## API endpoints

The API prefix is `/api/v1`.

| Group | Endpoints | Auth | Description |
|---|---|---|---|
| `health` | `GET /health` | No | Health check |
| `auth` | `POST /signup`, `/login`, `/refresh`, `/logout`, `GET /me` | Mixed | Authentication |
| `events` | `GET`, `POST`, `GET /{id}`, `PATCH /{id}`, `PATCH /{id}/approve`, `PATCH /{id}/reject`, `PATCH /{id}/assign-coordinator` | JWT | Event CRUD and moderation |
| `registrations` | `POST /`, `GET /my`, `GET /event/{id}`, `PATCH /{id}/accept`, `PATCH /{id}/reject` | JWT | Registration management |
| `attendance` | `POST /bulk`, `GET /event/{id}`, `GET /my` | JWT | Attendance tracking |
| `notifications` | `GET /`, `PATCH /{id}/read`, `POST /read-all` | JWT | In-app notifications |
| `reports` | `GET /dashboard` | JWT | Dashboard statistics |
| `users` | `GET /me`, `PATCH /me`, `GET /`, `PATCH /{id}/status` | JWT | User management |

## Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=app --cov-report=term-missing
```

The test suite covers **97%** of the codebase with 279 tests. Mocking strategy uses `AsyncMock` for async database sessions and `MagicMock` for SQLAlchemy models.

## Project structure

```
backend/
├── app/
│   ├── api/
│   │   ├── deps.py       # Auth dependencies (get_current_user, require_admin, etc.)
│   │   └── v1/           # Route handlers
│   ├── core/
│   │   ├── config.py     # Pydantic Settings with validators
│   │   ├── database.py   # Async SQLAlchemy engine and session factory
│   │   ├── exceptions.py # Custom exception classes + handlers
│   │   └── security.py   # JWT and bcrypt helpers
│   ├── middleware/
│   │   ├── security.py   # CSP, HSTS, X-Frame-Options headers
│   │   └── timeout.py    # Request timeout middleware
│   ├── models/           # SQLAlchemy ORM models
│   ├── schemas/          # Pydantic request/response schemas
│   └── services/         # Business logic layer
├── scripts/              # Data seeder and helpers
└── tests/                # pytest suite
```

## Tech stack

| Layer | Technology |
|---|---|
| Runtime | Python 3.12+ |
| Framework | FastAPI 0.138 |
| ASGI server | uvicorn 0.34 |
| ORM | SQLAlchemy 2.0 (async) |
| Database | SQLite (aiosqlite) |
| Auth | PyJWT + bcrypt |
| Validation | Pydantic v2 + Pydantic Settings |
| Logging | structlog |
| Testing | pytest, pytest-asyncio, httpx |

## Security

- All endpoints except health check require JWT Bearer authentication.
- Tokens use HS256 with configurable TTL; refresh tokens are rotated and blacklisted on logout.
- CORS restricted to configured origins.
- Security headers enforced: CSP, HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy.
- Rate limiting on all endpoints (100 req/min) with stricter limits on auth endpoints (20 req/min).
- Request timeout defaults to 30 seconds.
