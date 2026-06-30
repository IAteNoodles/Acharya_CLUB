# Acharya_CLUB — Backend Architecture Document

## 1. System Overview

Acharya_CLUB is a **College Event Management System** that digitizes the full lifecycle of student events — from proposal through approval, registration, attendance tracking, and reporting. The system serves three distinct roles:

| Role | Capabilities |
|---|---|
| **Student** | Browse events, register for events, view own attendance history, submit event proposals |
| **Teacher (Coordinator)** | Create and manage events, approve/reject student proposals, mark attendance, view event reports |
| **Admin** | Full system access: manage users, roles, all events, audit logs, system configuration |

**Core Workflows:**

1. **Event Creation → Approval** — A Teacher or Admin creates an event with details (title, description, date, venue, category, max registrations, college-only flag). Events require Admin approval if flagged as Out-College. In-College events created by Teachers are auto-approved but can be flagged for review.
2. **Registration → Confirmation** — Students browse published events and register. Registrations are capped at the event's maximum. Out-College events require additional fields (college name, ID card upload) and Admin confirmation.
3. **Attendance Tracking** — On the event date, the Teacher coordinator marks attendance for registered students. Attendance records are stored per-event per-student with timestamps.
4. **Notifications** — In-app notifications are created synchronously when events are approved/rejected, registrations are accepted/rejected, and teacher accounts are approved/rejected. Notifications are stored in the database and retrieved via GET endpoints. No email notification system exists yet.

---

## 2. Architecture Pattern: Modular Monolith

### Why Not Microservices

At the expected scale of hundreds of concurrent users within a single college campus, a microservices architecture introduces unnecessary operational complexity: multiple deployments, inter-service communication overhead, distributed transaction management, and higher infrastructure costs. A modular monolith provides:

- **Simpler deployment** — Single Docker image, one `docker compose up`
- **Lower latency** — In-process function calls instead of HTTP/gRPC between services
- **Atomic transactions** — SQLAlchemy can wrap cross-module operations in a single database transaction
- **Faster development velocity** — One codebase, shared Pydantic schemas, no versioning headaches
- **Sufficient scaling** — Vertical scaling (larger instance) and horizontal scaling (multiple read replicas) handle college-scale traffic

### Path to Extraction

Each module is encapsulated behind a clear interface boundary (thin service layer with async functions). If the system outgrows the monolith, individual modules can be extracted into separate services by:

1. Replacing direct function calls with HTTP/gRPC calls
2. Moving the module's database tables into a dedicated database
3. Adding an API gateway for routing

The module boundaries are designed so that **Events** and **Registrations** are the most likely candidates for early extraction due to their higher traffic and independent data lifecycle.

### Module Map

| Module | Responsibility | Actual Tables | Evidence |
|---|---|---|---|---|
| **Auth** | Signup, login, token issuance, refresh, logout | `users` (partial: email, password_hash) | `app/services/auth.py` |
| **Users** | Profile CRUD, role management, teacher approval/rejection | `users` | `app/services/user.py`, `app/api/v1/users.py` |
| **Events** | Event CRUD, approval workflow, coordinator assignment | `events` | `app/models/event.py`, `app/services/event.py` |
| **Registrations** | Student registration, accept/reject, capacity checks | `registrations` | `app/models/registration.py`, `app/services/registration.py` |
| **Attendance** | Bulk mark, attendance queries, status tracking | `attendance` | `app/models/attendance.py`, `app/services/attendance.py` |
| **Notifications** | In-app notification creation, listing, read status | `notifications` | `app/models/notification.py`, `app/services/notification.py` |
| **Reports** | Dashboard aggregate statistics | (query across all tables) | `app/services/reports.py` |

Actual table names use `__tablename__` (e.g., `events`, `registrations`, `attendance`, `notifications`, `users`). No `event_categories`, `student_profiles`, `refresh_tokens`, or `attendance_records` tables exist. Two Alembic migrations: `0001_initial_schema` (users, events, registrations, attendance) and `0002_notifications` (notifications).

---

## 3. Tech Stack

| Technology | Version | Purpose | Evidence |
|---|---|---|---|
| **Python** | 3.12+ (CI: 3.12, Docker: 3.13) | Runtime | `pyproject.toml:5`, `.github/workflows/ci.yml:19`, `Dockerfile:2` |
| **FastAPI** | >=0.138.0,<0.139.0 | HTTP Framework | Async-native, auto-generated OpenAPI docs, Pydantic v2 integration | `requirements.txt:2` |
| **Uvicorn** | 0.34.0 | ASGI Server | `requirements.txt:3` |
| **SQLAlchemy 2.0** | >=2.0.36 | Async ORM | `requirements.txt:4` |
| **asyncpg** | >=0.30.0 | PostgreSQL async driver | `requirements.txt:5` |
| **Alembic** | >=1.14.0 | DB Migrations | `requirements.txt:6` |
| **PyJWT[crypto]** | >=2.13.0 | JWT auth (HS256) | `requirements.txt:8`, `app/core/security.py:4` |
| **bcrypt** | >=4.2.0 | Password hashing | `requirements.txt:9`, `app/core/security.py:3` |
| **redis-py** | >=5.2.1 | Redis client (rate limiting) | `requirements.txt:10`, `app/core/redis.py:4` |
| **upstash-redis** | >=1.7.0 | REST-based Redis alternative | `requirements.txt:12`, `app/core/redis.py:8` |
| **structlog** | >=24.4.0 | Structured JSON logging | `requirements.txt:11`, `app/core/logging_config.py` |
| **pydantic-settings** | >=2.7.0 | Config from env/.env | `requirements.txt:7`, `app/core/config.py` |
| **Pydantic v2** | 2.x | Request/response validation | `app/schemas/*.py` |
| **PostgreSQL 16** (Supabase) | 16 | Primary database | `app/core/database.py`, `app/core/config.py:30` |
| **Redis 7** | 7.x | Rate limiting (sliding window) | `app/middleware/rate_limit.py:26` |

**Dev tooling:** pytest, pytest-asyncio, httpx, pytest-cov, fakeredis, testcontainers, psycopg2-binary.

**Not present in codebase (aspirational/planned):** Celery, boto3/S3, python-jose, passlib, SMTP/email service, Prometheus, audit_logs table, file upload endpoints. These are planned but not yet implemented.

---

## 4. Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                       # FastAPI app factory (create_app), lifespan, middleware, router registration
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py                 # pydantic-settings BaseSettings (DATABASE_URL auto-built from components)
│   │   ├── database.py               # async engine (NullPool in CI), async_sessionmaker, get_db generator
│   │   ├── redis.py                  # Redis async client singleton + Upstash REST fallback
│   │   ├── security.py               # JWT create/verify (PyJWT), password hash/verify (bcrypt)
│   │   ├── exceptions.py             # AppHTTPException hierarchy + register_exception_handlers
│   │   └── logging_config.py         # structlog JSON logger setup
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py                   # get_current_user, require_admin, require_teacher_or_admin, require_student
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── auth.py               # POST /signup, /login, /refresh, /logout
│   │       ├── users.py              # GET /users/me, PATCH /users/me, GET /users, PATCH /users/{id}/status
│   │       ├── events.py             # CRUD /events, POST /events/{id}/approve|reject|assign-coordinator
│   │       ├── registrations.py      # POST /, GET /my, GET /event/{id}, PATCH /{id}/accept|reject
│   │       ├── attendance.py         # POST /bulk, GET /event/{id}, GET /my
│   │       ├── notifications.py      # GET /, PATCH /{id}/read, POST /read-all
│   │       ├── reports.py            # GET /dashboard
│   │       ├── health.py             # GET /health (unauthenticated, unrate-limited)
│   │
│   ├── middleware/
│   │   ├── __init__.py
│   │   ├── rate_limit.py             # RedisRateLimiter + InMemoryRateLimiter fallback (strategy pattern)
│   │   ├── security.py               # SecurityHeadersMiddleware (CSP, HSTS, X-Frame-Options, etc.)
│   │   └── timeout.py                # RequestTimeoutMiddleware (default 30s)
│   │
│   ├── models/                       # SQLAlchemy 2.0 declarative models (all SAEnum with values_callable)
│   │   ├── __init__.py
│   │   ├── base.py                   # DeclarativeBase + TimestampMixin (UUID pk, created_at, updated_at)
│   │   ├── user.py                   # User (Role, UserStatus enums)
│   │   ├── event.py                  # Event (EventType, EventStatus, EventCategory enums)
│   │   ├── registration.py           # Registration (RegistrationStatus enum)
│   │   ├── attendance.py             # Attendance (AttendanceStatus enum)
│   │   └── notification.py           # Notification (NotificationType enum)
│   │
│   ├── schemas/                      # Pydantic v2 schemas (request/response)
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── users.py
│   │   ├── event.py
│   │   ├── registration.py
│   │   ├── attendance.py
│   │   ├── notification.py
│   │   ├── reports.py
│   │   └── common.py                 # PaginationParams, ErrorResponse, SuccessResponse
│   │
│   └── services/                     # Business logic layer (services use AsyncSession directly, no repo pattern)
│       ├── __init__.py
│       ├── auth.py                   # signup, login, refresh, logout, get_me (in-memory _blacklisted_tokens set)
│       ├── user.py                   # profile CRUD, role management
│       ├── event.py                  # event CRUD, approval workflow, coordinator assignment
│       ├── registration.py           # registration, capacity checks, accept/reject
│       ├── attendance.py             # bulk mark attendance, attendance queries
│       ├── notification.py           # create, list, mark_read, mark_all_read
│       └── reports.py                # dashboard aggregate stats (8 sequential DB queries)
│
├── alembic/                          # Alembic migrations
│   ├── versions/
│   │   ├── 0001_initial_schema.py    # Users, events, registrations, attendance tables
│   │   └── 0002_notifications.py     # Notifications table
│   ├── env.py                        # Alembic environment config (async run_async)
│   └── alembic.ini
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                   # app fixture → create_app()
│   ├── test_auth.py, test_auth_schemas.py, test_auth_service.py
│   ├── test_users.py
│   ├── test_events.py
│   ├── test_registrations.py
│   ├── test_attendance.py
│   ├── test_notifications.py, test_notification_schemas.py
│   ├── test_reports.py, test_reports_schemas.py
│   ├── test_common_schemas.py
│   ├── test_config.py, test_database.py, test_deps.py, test_exceptions.py
│   ├── test_health.py, test_logging_config.py, test_main.py
│   ├── test_rate_limit.py, test_redis.py, test_security.py, test_timeout.py
│   ├── test_e2e_workflows.py         # 6 E2E tests (testcontainers, marked @pytest.mark.e2e)
│   └── real_db/                      # Integration tests against real Supabase
│       ├── conftest.py               # Direct async engine from settings.DATABASE_URL (no testcontainers)
│       └── test_auth.py, test_users.py, test_events.py, test_registrations.py,
│           test_attendance.py, test_notifications.py, test_reports.py
│
├── scripts/
│   ├── entrypoint.sh                 # Docker entrypoint: alembic upgrade head → uvicorn
│   └── seed.py                       # Database seed script
│
├── .env.example                      # Supabase-first env template
├── pyproject.toml                    # Build config, dependencies, pytest markers
├── requirements.txt                  # Pinned dependencies (including dev: fakeredis, testcontainers, psycopg2-binary)
├── Dockerfile                        # Multi-stage Dockerfile (python:3.13-alpine)
├── docker-compose.yml                # Services: app (reads .env), postgres:16 (profile:local-db), redis:7 (profile:local-db)
├── docker-compose.prod.yml           # Production Docker Compose
├── uv.lock                           # UV lockfile for reproducible installs
└── README.md                         # Setup guide, API reference, testing instructions
```

---

## 5. Data Flow Diagrams

### 5.1 High-Level Request Lifecycle

Every authenticated API request follows this path through the system layers:

```
┌────────────────────────────────────────────────────────────────────────┐
│                          CLIENT (Mobile / Web)                         │
│              POST /api/v1/events  │  GET /api/v1/registrations/my      │
└────────────────────────┬───────────────────────────────────────────────┘
                         │ HTTP request (Bearer JWT)
                         ▼
┌────────────────────────────────────────────────────────────────────────┐
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                   MIDDLEWARE STACK (in order)                    │  │
│  │                                                                  │  │
│  │  1. CORSMiddleware           — CORS headers from whitelist       │  │
│  │  2. SecurityHeadersMiddleware — CSP, HSTS, X-Frame-Options       │  │
│  │  3. RequestTimeoutMiddleware  — 30s timeout per request          │  │
│  │  4. RateLimitMiddleware      — Sliding-window (Redis/in-memory)  │  │
│  │  5. RequestIDMiddleware      — UUID v4 per request + logging     │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└────────────────────────┬───────────────────────────────────────────────┘
                         ▼
┌────────────────────────────────────────────────────────────────────────┐
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                    FASTAPI ROUTER LAYER                          │  │
│  │                                                                  │  │
│  │  1. Route matching (/api/v1/registrations → registrations router)│  │
│  │  2. Path/query parameter extraction + Pydantic validation        │  │
│  │  3. Request body parsing + Pydantic schema validation (→ 422)    │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└────────────────────────┬───────────────────────────────────────────────┘
                         ▼
┌────────────────────────────────────────────────────────────────────────┐
│                DEPENDENCY INJECTION LAYER                             │
│                                                                       │
│  ┌──────────────────────┐    ┌────────────────────────────────────┐   │
│  │  get_current_user    │    │  get_db                           │   │
│  │  ┌──────────────┐    │    │  ┌─────────────────────────────┐  │   │
│  │  │ HTTPBearer   │    │    │  │ async_sessionmaker()        │  │   │
│  │  │ (parse token)│    │    │  │ → AsyncSession (scoped)     │  │   │
│  │  │ verify_token │    │    │  │ → yield session             │  │   │
│  │  │ is_blacklisted│   │    │  │ → close on response         │  │   │
│  │  │ → payload    │    │    │  └─────────────────────────────┘  │   │
│  │  └──────────────┘    │    └────────────────────────────────────┘   │
│  │  require_admin       │                                             │
│  │  require_student     │       ┌────────────────────────────────┐   │
│  │  require_teacher_or  │       │  get_redis()                   │   │
│  │    _admin            │       │  → redis.Redis client / None   │   │
│  └──────────────────────┘       └────────────────────────────────┘   │
└────────────────────────┬───────────────────────────────────────────────┘
                         ▼
┌────────────────────────────────────────────────────────────────────────┐
│                    SERVICE LAYER (Business Logic)                      │
│                                                                       │
│  RegistrationService.register(db, event_id, role_type, user)          │
│                                                                       │
│  1. db.get(Event, event_id)              → validate event exists     │
│  2. Check event.status == "approved"     → raise ConflictException   │
│  3. Check event.coordinator_id           → raise ConflictException   │
│  4. Check max_registrations capacity     → raise ConflictException   │
│  5. Check duplicate registration         → raise ConflictException   │
│  6. Registration(...) → db.add()         → INSERT                    │
│  7. db.commit() / db.refresh()           → persist + reload          │
│  8. Return Registration model                                       │
└────────────────────────┬───────────────────────────────────────────────┘
                         ▼
┌────────────────────────────────────────────────────────────────────────┐
│                  PERSISTENCE & EXTERNAL SERVICES                       │
│                                                                       │
│  ┌──────────────────────┐     ┌─────────────────────────────────┐     │
│  │     PostgreSQL 16    │     │          Redis 7                │     │
│  │     (Supabase)       │     │                                 │     │
│  │                      │     │  • Rate-limit counters          │     │
│  │  • users table       │     │    (sliding window sorted set)  │     │
│  │  • events table      │     │  • JWT blacklist               │     │
│  │  • registrations tbl │     │    (SETEX with TTL)             │     │
│  │  • attendance table  │     │                                 │     │
│  │  • notifications tbl │     │                                 │     │
│  └──────────────────────┘     └─────────────────────────────────┘     │
└────────────────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────────────────────┐
│                         RESPONSE                                      │
│                                                                       │
│  HTTP 200/201:  { "success": true, "data": { ... } }                 │
│  HTTP 4xx:      { "success": false, "error": { "code": ...,          │
│                   "message": ..., "details": [...] } }                │
│                                                                       │
│  Headers: X-Request-ID, X-RateLimit-Remaining, Content-Type          │
└────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Authentication Flow

```
┌──────────┐     ┌──────────┐     ┌──────────┐
│  Client  │     │   API    │     │    DB    │
└────┬─────┘     └────┬─────┘     └────┬─────┘
     │                 │                │
     │  POST /signup   │                │
     │ {name,email,    │                │
     │  password,role} │                │
     ├────────────────►│                │
     │                 │ Pydantic val.  │
     │                 │ bcrypt hash    │
     │                 │ Create user    │
     │                 ├───────────────►│
     │  {user,         │                │
     │   accessToken,  │                │
     │   refreshToken} │                │
     │◄────────────────┤                │
     │                 │                │
     │  POST /login    │                │
     │ {email,password}│                │
     ├────────────────►│                │
     │                 │ Pydantic val.  │
     │                 │ Fetch user     │
     │                 ├───────────────►│
     │                 │◄───────────────│
     │                 │ bcrypt verify  │
     │                 │ Sign tokens:   │
     │                 │ access(15min)  │
     │                 │ refresh(7d)    │
     │  {accessToken,  │                │
     │   refreshToken, │                │
     │   user}         │                │
     │◄────────────────┤                │
     │                 │                │
     │  GET /protected │                │
     │ Auth: Bearer    │                │
     ├────────────────►│                │
     │                 │ PyJWT verify   │
     │                 │ HS256 sig      │
│                 │ Check Redis    │
│                 │ blacklist      │
     │                 │ Depends()      │
     │                 │ injects user   │
     │                 │ Route handler  │
     │  {data}         │                │
     │◄────────────────┤                │
     │                 │                │
```

### 5.3 [PLANNED] File Upload Flow (Presigned S3 URLs)

Not yet implemented. No file upload endpoints, S3 client, or ClamAV scanning exist in the current codebase.

### 5.4 Attendance Marking Flow

```
┌──────────┐     ┌──────────┐     ┌──────────┐
│ Teacher  │     │   API    │     │    DB    │
│ (Client) │     └────┬─────┘     └────┬─────┘
└────┬─────┘          │                │
     │                │                │
     │  GET /events/:id/registrations  │
     │  (view registered students)     │
     ├────────────────►│                │
     │                 │ Fetch students │
     │                 │ registered &   │
     │                 │ approved       │
     │                 ├───────────────►│
     │                 │◄───────────────│
     │  {students[]}   │                │
     │◄────────────────┤                │
     │                 │                │
     │  POST /attendance/bulk           │
     │  {records: [    │                │
     │   {studentId,   │                │
     │    status:      │                │
     │    "present"|   │                │
     │    "absent"}]   │                │
     ├────────────────►│                │
     │                 │ Pydantic val.  │
     │                 │ Check teacher  │
     │                 │ is coordinator │
     │                 │ for this event │
     │                 │ Bulk upsert    │
     │                 ├───────────────►│
     │                 │ (transaction)  │
     │  {success:true, │                │
     │   count: 45}    │                │
     │◄────────────────┤                │
     │                 │                │
```

### 5.5 Notification Flow (In-App, Synchronous)

Notifications are created synchronously within the same request as the triggering action (event approve/reject, registration accept/reject, teacher approve/reject). They are stored in the `notifications` table and retrieved via GET endpoints. No email/Celery async flow is implemented.

[PLANNED: Email notifications via Celery or Cloudflare Email Workers]

---

## 6. Security Architecture

### 6.1 Authentication & Token Management

- **JWT with HS256** (symmetric key from env `JWT_SECRET`). Access tokens expire in **15 minutes**. Refresh tokens expire in **7 days**. JWT_SECRET is auto-generated in development if not provided.
- **Refresh token rotation**: Every time a refresh token is used, the old token is added to an in-memory blacklist (`_blacklisted_tokens` set) and a new one issued. If a rotated-out token is ever reused, it is rejected.
- **Token blacklist**: An in-memory `set()` at `app/services/auth.py:16` holds revoked refresh tokens. Blacklist is **not persisted** — reset on each restart. Not shared across uvicorn workers.
- **Email verification**: [PLANNED — Not yet implemented. No email sending capability exists.]

### 6.2 Role-Based Access Control (RBAC)

Actual dependencies in `app/api/deps.py`:
- `get_current_user` — verifies JWT, checks in-memory blacklist, returns payload dict
- `require_admin` — checks `current_user.get("role") == "admin"`
- `require_teacher_or_admin` — checks `role in ("teacher", "admin")`
- `require_student` — checks `role == "student"`

No `require_role` factory or `ROLE_HIERARCHY` dict exists. The checks are explicit string comparisons per dependency function.

### 6.3 Input Validation

- Every endpoint uses a **Pydantic v2 schema** that validates request body, query parameters, and path parameters via FastAPI's built-in validation.
- FastAPI automatically returns a 422 response with field-level error details if validation fails.
- `model_validator` and `field_validator` decorators enable complex cross-field validation (e.g., end_date > start_date).
- This prevents malformed or malicious input from reaching business logic or the database.

### 6.4 Rate Limiting

| Scope | Limit | Backend |
|---|---|---|
| General API | 100 requests per minute per IP | Redis sliding window (or in-memory fallback) |
| Authentication (login, signup) | 20 requests per minute per IP | Redis sliding window (or in-memory fallback) |

Rate limiter uses a strategy pattern (`app/middleware/rate_limit.py`): `RedisRateLimiter` when Redis is configured, `InMemoryRateLimiter` (per-process dict) as fallback. In-memory fallback is NOT accurate under multi-worker deployments.

### 6.5 HTTP Security Headers

FastAPI middleware is configured with strict defaults (via `Starlette` middleware or custom ASGI middleware):

- `Content-Security-Policy`: restricts script/style sources to origin
- `Strict-Transport-Security`: max-age=31536000, includeSubDomains
- `X-Content-Type-Options`: nosniff
- `X-Frame-Options`: DENY
- `X-XSS-Protection`: 0 (modern browsers disable this; reliance is on CSP)

### 6.6 CORS

CORS is configured via FastAPI's `CORSMiddleware` with an explicit whitelist read from `CORS_ORIGINS` env variable (comma-separated). In production, this is the college domain and any trusted subdomains. In development, it includes `http://localhost:5173` (Vite dev server).

### 6.7 File Upload Security

[PLANNED — Not yet implemented. No file upload endpoints exist.]

### 6.8 Password Hashing

**bcrypt** (direct, not passlib) is used with the following parameters:

| Parameter | Value |
|---|---|
| Algorithm | bcrypt (via `bcrypt.gensalt()` — default rounds) |
| Rounds (cost factor) | Default (12) |
| Salt | Auto-generated |

Implemented in `app/core/security.py:52-57`. Cost factor is not configurable via env var.

### 6.9 SQL Injection Prevention

All database queries go through **SQLAlchemy 2.0** which uses parameterized queries under the hood. Raw SQL via `text()` is not prevented by an active linter — no ruff/flake8 enforcement is configured.

### 6.10 Audit Logging

[PLANNED — Not yet implemented. No `audit_logs` table exists.]

---

## 7. Caching Strategy

[PLANNED — No cache-aside pattern is currently implemented in any service layer. All queries go directly to the database.]

Current state:
- **Rate limit counters**: Use Redis sorted sets (or in-memory dict fallback). This is the only cached data in the system.
- **Token blacklist**: In-memory Python `set()`, not Redis.
- **All other data**: Direct SQLAlchemy queries on every request.

Planned caching (not implemented):
- Event listings: Cache-aside with 5min TTL
- User profiles: Cache-aside with 15min TTL
- Dashboard stats: Cache-aside with 10min TTL

---

## 8. Error Handling

### 8.1 Consistent Response Format

Error responses follow this structure (from `app/core/exceptions.py`):

```python
{
    "success": False,
    "error": {
        "code": "VALIDATION_ERROR",     # Machine-readable error code
        "message": "Validation failed",  # Human-readable detail
        "details": [...]                 # Optional; present for ValidationException
    }
}
```

Success responses do not follow a standardized envelope — data shape depends on the endpoint.

### 8.2 Exception Class Hierarchy

```
AppHTTPException (base, extends Exception — NOT HTTPException)
├── NotFoundException       → 404 — error_code="NOT_FOUND"
├── UnauthorizedException   → 401 — error_code="UNAUTHORIZED" (+ WWW-Authenticate header)
├── ForbiddenException      → 403 — error_code="FORBIDDEN"
├── ValidationException     → 422 — error_code="VALIDATION_ERROR" (+ errors list)
└── ConflictException       → 409 — error_code="CONFLICT"
```

Each accepts `detail` (str) and optional `error_code` (str). `ValidationException` additionally accepts an `errors` (list of dicts) for field-level details.

### 8.3 Exception Handlers

Registered via `register_exception_handlers(app)` in `app/core/exceptions.py:73`. Three handlers:

1. **AppHTTPException** — Returns JSON with `status_code`, `error_code`, `detail`. For `ValidationException`, also serializes `errors`.
2. **StarletteHTTPException** — Catches FastAPI/Starlette HTTP errors (e.g., 405, 404 from router). Maps 404→`"NOT_FOUND"`, others→`"HTTP_ERROR"`.
3. **Generic Exception** — All unhandled exceptions return `500` with `"INTERNAL_ERROR"` code. No stack trace exposed to client.

No RequestValidationError or SQLAlchemy-specific handlers are registered. No development-mode stack trace exposure.

---

## 9. Logging & Monitoring

### 9.1 Structured Logging with structlog

All logs are output as newline-delimited JSON (via `JSONRenderer`). No pretty-printing or dev console renderer configured.

Actual config from `app/core/logging_config.py`:

```python
structlog.configure(
    processors=[
        add_log_level,
        TimeStamper(fmt="iso"),
        structlog.processors.UnicodeDecoder(),
        JSONRenderer(),
    ],
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)
```

**Log levels used:** `info`, `warning`, `error` (via structlog stdlib integration).

### 9.2 Request Correlation IDs

A custom ASGI middleware (`app/main.py:156-162`) generates a UUIDv4 per request:

- Bound via `structlog.contextvars.bound_contextvars(request_id=...)` for structured logging
- Returned as `X-Request-ID` response header
- NOT stored on `request.state` — only available via structlog context vars

### 9.3 Health Check Endpoints

| Endpoint | Checks |
|---|---|
| `GET /api/v1/health` | Returns `{"status": "ok"}` immediately — no DB or Redis ping |

Only one health endpoint exists. No `/health/ready` endpoint. Not rate-limited, not authenticated. Used by Docker HEALTHCHECK.

### 9.4 Prometheus Metrics

[PLANNED — Not yet implemented. No prometheus-fastapi-instrumentator, no `/metrics` endpoint, no OpenTelemetry integration.]

---

## 10. Deployment Architecture

### 10.1 Dockerfile

From `backend/Dockerfile`:

```dockerfile
FROM python:3.13-alpine AS development
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
COPY scripts/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

Single-stage development image. Production image uses a separate `docker-compose.prod.yml`. Entrypoint runs `alembic upgrade head` before starting the server.

### 10.2 Docker Compose (Local Development)

From `backend/docker-compose.yml`:

```yaml
services:
  app:
    build:
      context: .
      target: development
    ports:
      - "8000:8000"
    env_file:
      - .env
    environment:
      - ENVIRONMENT=development
      - DEBUG=true
      - CORS_ORIGINS=["http://localhost:5173","http://localhost:8000"]
    volumes:
      - .:/app
      - /app/__pycache__
    command: uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000 --reload
    healthcheck:
      test: ["CMD", "curl", "-sf", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 3s
      start_period: 10s
      retries: 3

  postgres:
    image: postgres:16-alpine
    profiles: ["local-db"]
    ports: ["5432:5432"]
    volumes: [pgdata:/var/lib/postgresql/data]

  redis:
    image: redis:7-alpine
    profiles: ["local-db"]
    ports: ["6379:6379"]
    volumes: [redisdata:/data]

volumes:
  pgdata:
  redisdata:
```

Note: The `app` service reads credentials from `.env` (default: Supabase URL). The `postgres` and `redis` services are gated behind `--profile local-db` and are not started by default with `docker compose up`. No Celery worker service exists.

### 10.3 Environment Configuration

All configuration is loaded from environment variables and validated by pydantic-settings at import time. From `app/core/config.py`:

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore")

    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    API_PREFIX: str = "/api/v1"

    DATABASE_URL: str = ""           # If empty, auto-built from DB_* components
    DB_USER: str = "postgres.qwouxrnnwmkotkwraqme"
    DB_PASSWORD: str = ""
    DB_HOST: str = "aws-1-ap-northeast-1.pooler.supabase.com"
    DB_PORT: int = 5432
    DB_NAME: str = "postgres"

    REDIS_URL: str = "redis://localhost:6379/0"

    JWT_SECRET: str = ""             # Auto-generated random in development
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_EXPIRE_DAYS: int = 7

    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:8000"]
    LOG_LEVEL: str = "INFO"
```

| Variable | Required | Description |
|---|---|---|
| `ENVIRONMENT` | No (default: development) | `development`, `production`, or `test` |
| `DATABASE_URL` | Conditional | Full asyncpg URL; if empty, requires `DB_PASSWORD` |
| `DB_PASSWORD` | Conditional | Supabase password — constructs URL from hardcoded defaults |
| `REDIS_URL` | No (default: localhost:6379) | Redis connection string |
| `JWT_SECRET` | Conditional | Auto-generated in development; required in production (min 32 chars) |
| `CORS_ORIGINS` | No | JSON string array |

### 10.4 Deployment Strategy

**Blue-Green Deployment** is used to minimize downtime:

1. A new version (green) is deployed alongside the current version (blue).
2. Database migrations run first (as a separate CI/CD step, not at app startup) using `alembic upgrade head`.
3. The green version starts and passes health checks.
4. The load balancer switches traffic from blue to green.
5. The blue version is terminated after a cooldown period.

**CI/CD Pipeline:**

```
Push to main → Build Docker image → Push to registry →
  Run migrations (alembic upgrade head) → Deploy green → Smoke tests →
  Switch traffic → Terminate blue
```

### 10.5 Database Migrations

Migrations are run as an **explicit CI/CD step** before the new application version is deployed, never at application startup. This prevents:

- Multiple instances racing to run migrations simultaneously
- Rollbacks being complicated by auto-migrations
- Application startup failures due to migration errors

The migration step uses `alembic upgrade head` (not `alembic revision --autogenerate`, which is for local development only).

```bash
# CI/CD step
alembic upgrade head
```

---

## 11. Decision Log

| # | Decision | Option Chosen | Alternatives Considered | Rationale |
|---|---|---|---|---|
| 1 | **Architecture** | Modular Monolith | Microservices | Lower operational burden at current scale (hundreds of concurrent users). Clear module boundaries allow future extraction if needed. Microservices would add distributed transaction complexity, service mesh overhead, and require multiple deployments. |
| 2 | **Framework** | FastAPI | Flask, Django, Starlette | FastAPI is async-native with auto-generated OpenAPI docs, Pydantic v2 integration, and dependency injection — zero boilerplate for validation and documentation. Flask lacks async support and validation infrastructure. Django is monolithic and heavy for a pure API service. Starlette is lower-level (FastAPI is built on it) and would require manual OpenAPI generation. |
| 3 | **ORM** | SQLAlchemy 2.0 (async) | Django ORM, Tortoise-ORM, GINO | SQLAlchemy 2.0 is the most mature Python ORM with full async support via asyncpg. Its declarative mapping with type annotations, relationship loading strategies, and comprehensive query API make it superior for complex queries. Django ORM is tightly coupled to Django. Tortoise-ORM is less battle-tested. |
| 4 | **Validation** | Pydantic v2 | attrs, msgspec, marshmallow | Pydantic v2's Rust-core engine (pydantic-core) provides 5-50x faster validation than v1. It is the default validation layer for FastAPI. |
| 5 | **Authentication** | JWT (access + refresh tokens, PyJWT[crypto]) | Sessions (Starlette), python-jose | JWT is stateless — no database lookup on every request. PyJWT chosen over python-jose for broader maintenance and HS256 support. |
| 6 | **Password Hashing** | bcrypt (direct) | passlib[bcrypt], argon2-cffi | Direct bcrypt used instead of passlib for simplicity. Cost factor 12 via default `bcrypt.gensalt()`. |
| 7 | **File Uploads** | [PLANNED] Presigned S3 URLs | N/A | Not yet implemented. |
| 8 | **Background Jobs** | [REJECTED] Celery removed from requirements | In-process async | Celery not needed — notifications are synchronous/in-app. Can be added later if email async is needed. |
| 9 | **Logging** | structlog | logging (stdlib), loguru | structlog with JSONRenderer for structured logs, request-ID middleware for traceability. |
| 10 | **API Documentation** | FastAPI auto OpenAPI | Manual OpenAPI, Apispec | FastAPI auto-generates OpenAPI 3.1 spec; served at `/api/v1/docs` and `/api/v1/redoc`. |
| 11 | **Database** | PostgreSQL 16 (Supabase) | MySQL 8, SQLite, MongoDB | Supabase managed Postgres with PgBouncer pooler. ACID compliant, managed backups, connection pooling. |
| 12 | **Cache** | Redis (redis-py + upstash-redis) | In-memory dict, Memcached | Redis used for rate limiting (sliding window). Upstash Redis available as REST-based alternative. |
| 13 | **Deployment** | Docker (single-stage) | Blue-Green, Serverless | Single Dockerfile for dev; `docker-compose.prod.yml` for production. Blue-green deployment planned. |
| 14 | **Migrations** | Docker entrypoint + CI step | App startup auto-migration | `alembic upgrade head` runs at Docker entrypoint and as CI step — not at application startup. |

(End of file - total 729 lines)
