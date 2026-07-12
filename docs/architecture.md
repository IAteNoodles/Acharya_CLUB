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

- **Simpler deployment** — One command to run `uvicorn`
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
|---|---|---|---|
| **Auth** | Signup, login, token issuance, refresh, logout | `users` (partial: email, password_hash) | `app/services/auth.py` |
| **Users** | Profile CRUD, role management, teacher approval/rejection | `users` | `app/services/user.py`, `app/api/v1/users.py` |
| **Events** | Event CRUD, approval workflow, coordinator assignment | `events` | `app/models/event.py`, `app/services/event.py` |
| **Registrations** | Student registration, accept/reject, capacity checks | `registrations` | `app/models/registration.py`, `app/services/registration.py` |
| **Attendance** | Bulk mark, attendance queries, status tracking | `attendance` | `app/models/attendance.py`, `app/services/attendance.py` |
| **Notifications** | In-app notification creation, listing, read status | `notifications` | `app/models/notification.py`, `app/services/notification.py` |
| **Reports** | Dashboard aggregate statistics | (query across all tables) | `app/services/reports.py` |

Actual table names use `__tablename__` (e.g., `events`, `registrations`, `attendance`, `notifications`, `users`).

---

## 3. Tech Stack

| Technology | Version | Purpose | Evidence |
|---|---|---|---|
| **Python** | 3.12+ | Runtime | `pyproject.toml:5` |
| **FastAPI** | >=0.138.0,<0.139.0 | HTTP Framework | Async-native, auto-generated OpenAPI docs, Pydantic v2 integration | `requirements.txt:2` |
| **Uvicorn** | 0.34.0 | ASGI Server | `requirements.txt:3` |
| **SQLAlchemy 2.0** | >=2.0.36 | Async ORM | `requirements.txt:4` |
| **aiosqlite** | >=0.30.0 | SQLite async driver | `requirements.txt:5` |
| **PyJWT[crypto]** | >=2.13.0 | JWT auth (HS256) | `requirements.txt:8`, `app/core/security.py:4` |
| **bcrypt** | >=4.2.0 | Password hashing | `requirements.txt:9`, `app/core/security.py:3` |
| **structlog** | >=24.4.0 | Structured JSON logging | `requirements.txt:11`, `app/core/logging_config.py` |
| **pydantic-settings** | >=2.7.0 | Config from env/.env | `requirements.txt:7`, `app/core/config.py` |
| **Pydantic v2** | 2.x | Request/response validation | `app/schemas/*.py` |
| **SQLite**  | 3.x | Primary database | `app/core/database.py`, `app/core/config.py:30` |

**Dev tooling:** pytest, pytest-asyncio, httpx, pytest-cov

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
│   │   ├── database.py               # async engine, async_sessionmaker, get_db generator
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
│   │       ├── health.py             # GET /health (unauthenticated)
│   │
│   ├── middleware/
│   │   ├── __init__.py
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
│   ├── test_security.py, test_timeout.py
│   └── test_e2e_workflows.py         # E2E tests using ephemeral SQLite DB
│
├── scripts/
│   └── seed.py                       # Database seed script
│
├── .env.example                      # SQLite-first env template
├── pyproject.toml                    # Build config, dependencies, pytest markers
├── requirements.txt                  # Pinned dependencies
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
│  │  4. RequestIDMiddleware      — UUID v4 per request + logging     │  │
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
│  │  require_student     │                                             │
│  │  require_teacher_or  │                                             │
│  │    _admin            │                                             │
│  └──────────────────────┘                                             │
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
│  ┌──────────────────────┐                                             │
│  │     SQLite           │                                             │
│  │                      │                                             │
│  │  • users table       │                                             │
│  │  • events table      │                                             │
│  │  • registrations tbl │                                             │
│  │  • attendance table  │                                             │
│  │  • notifications tbl │                                             │
│  └──────────────────────┘                                             │
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
│  Headers: X-Request-ID, Content-Type                                  │
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
     │                 │ Check blacklist│
     │                 │ (in-memory)    │
     │                 │ Depends()      │
     │                 │ injects user   │
     │                 │ Route handler  │
     │  {data}         │                │
     │◄────────────────┤                │
     │                 │                │
```

---

## 6. Security Architecture

### 6.1 Authentication & Token Management

- **JWT with HS256** (symmetric key from env `JWT_SECRET`). Access tokens expire in **15 minutes**. Refresh tokens expire in **7 days**. JWT_SECRET is auto-generated in development if not provided.
- **Refresh token rotation**: Every time a refresh token is used, the old token is added to an in-memory blacklist (`_blacklisted_tokens` set) and a new one issued. If a rotated-out token is ever reused, it is rejected.
- **Token blacklist**: An in-memory `set()` at `app/services/auth.py:16` holds revoked refresh tokens. Blacklist is **not persisted** — reset on each restart. Not shared across uvicorn workers.

### 6.2 Role-Based Access Control (RBAC)

Actual dependencies in `app/api/deps.py`:
- `get_current_user` — verifies JWT, checks in-memory blacklist, returns payload dict
- `require_admin` — checks `current_user.get("role") == "admin"`
- `require_teacher_or_admin` — checks `role in ("teacher", "admin")`
- `require_student` — checks `role == "student"`

The checks are explicit string comparisons per dependency function.

### 6.3 Input Validation

- Every endpoint uses a **Pydantic v2 schema** that validates request body, query parameters, and path parameters via FastAPI's built-in validation.
- FastAPI automatically returns a 422 response with field-level error details if validation fails.
- `model_validator` and `field_validator` decorators enable complex cross-field validation (e.g., end_date > start_date).
- This prevents malformed or malicious input from reaching business logic or the database.

### 6.4 HTTP Security Headers

FastAPI middleware is configured with strict defaults:

- `Content-Security-Policy`: restricts script/style sources to origin (and allows Swagger CDN resources)
- `Strict-Transport-Security`: max-age=31536000, includeSubDomains
- `X-Content-Type-Options`: nosniff
- `X-Frame-Options`: DENY
- `X-XSS-Protection`: 0 (modern browsers disable this; reliance is on CSP)

### 6.5 CORS

CORS is configured via FastAPI's `CORSMiddleware` with an explicit whitelist read from `CORS_ORIGINS` env variable (comma-separated).

### 6.6 Password Hashing

**bcrypt** is used with the default rounds (12) and auto-generated salts.

### 6.7 SQL Injection Prevention

All database queries go through **SQLAlchemy 2.0** which uses parameterized queries under the hood.

---

## 7. Caching Strategy

All database queries go directly to the SQLite database. Revoked refresh tokens are stored in an in-memory python `set()`. No caching engine (like Redis) is deployed.

---

## 8. Error Handling

### 8.1 Consistent Response Format

Error responses follow this structure:

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

### 8.2 Exception Class Hierarchy

```
AppHTTPException (base, extends Exception — NOT HTTPException)
├── NotFoundException       → 404 — error_code="NOT_FOUND"
├── UnauthorizedException   → 401 — error_code="UNAUTHORIZED" (+ WWW-Authenticate header)
├── ForbiddenException      → 403 — error_code="FORBIDDEN"
├── ValidationException     → 422 — error_code="VALIDATION_ERROR" (+ errors list)
└── ConflictException       → 409 — error_code="CONFLICT"
```

---

## 9. Logging & Monitoring

### 9.1 Structured Logging with structlog

All logs are output as newline-delimited JSON (via `JSONRenderer`).

### 9.2 Request Correlation IDs

A custom ASGI middleware (`app/main.py`) generates a UUIDv4 per request, bound to the structlog context and returned as the `X-Request-ID` response header.

### 9.3 Health Check Endpoints

| Endpoint | Checks |
|---|---|
| `GET /api/v1/health` | Returns `{"status": "ok"}` immediately |

---

## 10. Deployment Architecture

### 10.1 Local Environment

The application is designed to run locally using Uvicorn without any external dependencies.

```bash
uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000 --reload
```

### 10.2 Database

Data is stored locally in `acharya_club.db`. The schema is created automatically on startup by `Base.metadata.create_all`.

---

## 11. Decision Log

| # | Decision | Option Chosen | Alternatives Considered | Rationale |
|---|---|---|---|---|
| 1 | **Architecture** | Modular Monolith | Microservices | Lower operational burden at current scale. Clear module boundaries allow future extraction if needed. |
| 2 | **Framework** | FastAPI | Flask, Django, Starlette | FastAPI is async-native with auto-generated OpenAPI docs, Pydantic v2 integration, and dependency injection. |
| 3 | **ORM** | SQLAlchemy 2.0 (async) | Django ORM, Tortoise-ORM | SQLAlchemy 2.0 is mature with full async support via aiosqlite. |
| 4 | **Validation** | Pydantic v2 | attrs, msgspec, marshmallow | Pydantic v2's Rust-core engine provides fast validation. It is the default validation layer for FastAPI. |
| 5 | **Authentication** | JWT (access + refresh tokens) | Sessions (Starlette), python-jose | JWT is stateless — no database lookup on every request. |
| 6 | **Password Hashing** | bcrypt (direct) | passlib[bcrypt] | Direct bcrypt used instead of passlib for simplicity. |
| 7 | **Background Jobs** | In-process async | Celery | Celery not needed — notifications are synchronous/in-app. |
| 8 | **Logging** | structlog | logging (stdlib) | structlog with JSONRenderer for structured logs, request-ID middleware for traceability. |
| 9 | **API Documentation** | FastAPI auto OpenAPI | Manual OpenAPI | FastAPI auto-generates OpenAPI 3.1 spec; served at `/api/v1/docs` and `/api/v1/redoc`. |
| 10 | **Database** | SQLite | PostgreSQL, MySQL | Local SQLite file. Zero config, simple local development, no containers. |
| 11 | **Cache** | None | Redis, Memcached | Redis rate-limiter and cache removed; in-memory lists/sets are used where transient tracking is needed. |
| 12 | **Deployment** | Bare Metal / Local | Docker | Simple local startup via Uvicorn. |
| 13 | **Migrations** | Startup Generation | Alembic | `Base.metadata.create_all` runs on application startup. |
