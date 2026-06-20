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
4. **Notifications** — Email notifications are sent asynchronously for registration confirmations, event reminders, approval status changes, and attendance summaries.

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

| Module | Responsibility | Tables |
|---|---|---|
| **Auth** | Signup, login, token issuance, token refresh, logout, email verification | `users` (partial), `refresh_tokens` |
| **Users** | Profile CRUD, role management, student/teacher/admin data | `users`, `student_profiles` |
| **Events** | Event CRUD, approval workflow, category management | `events`, `event_categories` |
| **Registrations** | Student registration, waitlist, cancellation, confirmation | `registrations` |
| **Attendance** | Marking attendance, attendance reports, bulk operations | `attendance_records` |

---

## 3. Tech Stack

| Technology | Version | Purpose | Rationale |
|---|---|---|---|
| **Python** | 3.12+ | Runtime | Modern type hints (PEP 695), improved asyncio, faster interpreter; excellent ecosystem for data-heavy and I/O-bound services |
| **FastAPI** | 0.115+ | HTTP Framework | Async-native, auto-generates OpenAPI/Swagger docs, Pydantic v2 integration for request/response validation, dependency injection system eliminates boilerplate middleware |
| **SQLAlchemy 2.0** | 2.0+ | ORM | Mature, async-native (async session + asyncpg), declarative mapping with Python type annotations, rich query API with relationship loading strategies |
| **Alembic** | — | Migrations | Industry-standard migration tool for SQLAlchemy; autogenerate support, arbitrary migration directives, branching/merging |
| **PostgreSQL** | 16 | Primary Database | ACID-compliant, advanced indexing (B-tree, GiST, GIN), JSONB for flexible fields, mature and reliable |
| **Redis** | 7.x | Cache + Queue Backend | In-memory data store for sub-millisecond reads; also serves as the backing store for Celery result backend and rate limiting |
| **redis-py** | 5.x | Redis Client | Official Python Redis client with async support (`aioredis` merged into redis-py 5+), connection pooling, clustering support |
| **Pydantic v2** | 2.x | Validation | Rust-core engine (pydantic-core) for 5-50x faster validation; `BaseModel` with `model_validator`/`field_validator`; first-class FastAPI integration for request/response serialization |
| **python-jose** | 3.x | JWT Implementation | Pure-Python JWT library with support for multiple algorithms (HS256, RS256, ES256); integrates cleanly with FastAPI dependency injection |
| **passlib[bcrypt]** | — | Password Hashing | Industry-standard bcrypt implementation; OWASP-recommended cost factor of 12; passlib provides a unified hashing API with automatic salt management |
| **boto3** | — | S3 Client | Official AWS SDK for Python; presigned URL generation, object upload/download, bucket policies |
| **Celery** | — | Background Jobs | Distributed task queue with Redis broker; built-in retries, rate limiting, task routing, periodic tasks (celery beat), and Flower monitoring UI |
| **structlog** | — | Logging | Structured logging with processor pipelines; bound loggers for request-scoped context (correlation IDs), JSON output via `structlog.processors.JSONRenderer` |
| **pydantic-settings** | — | Configuration | `BaseSettings` with `.env` file loading, field validation, secret handling, `SettingsConfigDict` for flexible configuration management |
| **httpx** | — | HTTP Client | Async HTTP client used in tests via `AsyncClient` to invoke the FastAPI app without a live server |
| **FastAPI auto OpenAPI** | — | API Documentation | FastAPI automatically generates OpenAPI 3.1 spec from route definitions, Pydantic schemas, and docstrings; served at `/docs` (Swagger) and `/redoc` (ReDoc) with zero additional configuration |

---

## 4. Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                       # FastAPI app creation, lifespan, CORS middleware, exception handlers
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py                 # pydantic-settings BaseSettings (validated at import time)
│   │   ├── database.py               # async engine, async_sessionmaker, get_db dependency generator
│   │   ├── redis.py                  # Redis async client singleton
│   │   ├── security.py               # JWT create/verify (python-jose), password hash/verify (passlib)
│   │   └── exceptions.py             # Custom AppHTTPException subclasses
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py                   # FastAPI dependencies: get_current_user, get_current_admin_user, etc.
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py             # Aggregates all v1 routers via app.include_router
│   │       ├── auth.py               # POST /signup, /login, /refresh, /logout, /verify-email
│   │       ├── users.py              # GET/PATCH /users/me, GET /users (admin), PATCH /users/{id}/role
│   │       ├── events.py             # CRUD /events, POST /events/{id}/approve, POST /events/{id}/reject
│   │       ├── registrations.py      # POST /events/{id}/register, DELETE /registrations/{id}
│   │       └── attendance.py         # POST /attendance/bulk, GET /attendance/sheet
│   │
│   ├── models/                       # SQLAlchemy 2.0 declarative models
│   │   ├── __init__.py
│   │   ├── base.py                   # DeclarativeBase with common columns (id, created_at, updated_at)
│   │   ├── user.py                   # User model
│   │   ├── event.py                  # Event model
│   │   ├── registration.py           # Registration model
│   │   └── attendance.py             # AttendanceRecord model
│   │
│   ├── schemas/                      # Pydantic v2 schemas (request/response)
│   │   ├── __init__.py
│   │   ├── auth.py                   # SignupRequest, LoginRequest, TokenResponse, RefreshRequest
│   │   ├── user.py                   # UserResponse, UserUpdate, AssignRoleRequest
│   │   ├── event.py                  # EventCreate, EventResponse, EventUpdate, EventQueryParams
│   │   ├── registration.py           # RegistrationResponse, RegisterRequest
│   │   └── attendance.py             # BulkAttendanceRequest, AttendanceRecordResponse
│   │
│   └── services/                     # Business logic layer
│       ├── __init__.py
│       ├── auth.py                   # signup, login, refresh_tokens, logout, verify_email
│       ├── user.py                   # get_profile, update_profile, assign_role, list_users
│       ├── event.py                  # create_event, list_events, approve_event, reject_event
│       ├── registration.py           # register_student, cancel_registration, capacity_check
│       └── attendance.py             # mark_attendance_bulk, get_attendance_sheet, get_my_attendance
│
├── alembic/                          # Alembic migrations
│   ├── versions/                     # Auto-generated migration scripts
│   ├── env.py                        # Alembic environment config (async run_async)
│   └── alembic.ini                   # Alembic configuration (sqlalchemy.url reference)
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                   # Fixtures: async test client, test database, auth headers
│   ├── test_auth.py
│   ├── test_users.py
│   ├── test_events.py
│   ├── test_registrations.py
│   └── test_attendance.py
│
├── scripts/
│   ├── seed.py                       # Database seed script: creates admin user, sample events, categories
│   └── seed_data.py                  # Raw seed data constants (event titles, dummy student list)
│
├── pyproject.toml                    # Build config, dependencies, tool settings (ruff, pytest)
├── requirements.txt                  # Pinned dependencies for reproducible builds
├── Dockerfile                        # Multi-stage build: deps → install → production image
├── docker-compose.yml                # Services: app (uvicorn hot-reload), postgres:16, redis:7
└── .env.example                      # Documented env template with all variables
```

---

## 5. Data Flow Diagrams

### 5.1 Authentication Flow

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  Client  │     │   API    │     │   DB     │     │   Redis   │
└────┬─────┘     └────┬─────┘     └────┬─────┘     └────┬──────┘
     │                 │                │                │
     │  POST /signup   │                │                │
     │ {email,pass,...}│                │                │
     ├────────────────►│                │                │
     │                 │ Pydantic val.  │                │
     │                 │ passlib hash   │                │
     │                 │ Create user    │                │
     │                 ├───────────────►│                │
     │                 │                │                │
     │                 │ Enqueue email  │                │
     │                 │ (verify mail)  │                │
     │  {success:true} │                │                │
     │◄────────────────┤                │                │
     │                 │                │                │
     │  POST /login    │                │                │
     │ {email,password}│                │                │
     ├────────────────►│                │                │
     │                 │ Pydantic val.  │                │
     │                 │ Fetch user     │                │
     │                 ├───────────────►│                │
     │                 │◄───────────────┤                │
     │                 │ passlib verify │                │
     │                 │ Sign tokens:   │                │
     │                 │ access(15min)  │                │
     │                 │ refresh(7d)    │                │
     │                 │ Store refresh  │                │
     │                 │ token hash     │                │
     │                 ├───────────────►│                │
     │ {accessToken,   │                │                │
     │  refreshToken,  │                │                │
     │  user}          │                │                │
     │◄────────────────┤                │                │
     │                 │                │                │
     │  GET /protected │                │                │
     │ Auth: Bearer    │                │                │
     ├────────────────►│                │                │
     │                 │ python-jose    │                │
     │                 │ verify JWT sig │                │
     │                 │ Check blacklist│                │
     │                 ├───────────────►│ exists?        │
     │                 │◄───────────────│ no             │
     │                 │ Depends()      │                │
     │                 │ injects user   │                │
     │                 │ Route handler  │                │
     │  {data}         │                │                │
     │◄────────────────┤                │                │
     │                 │                │                │
```

### 5.2 File Upload Flow (Presigned S3 URLs)

```
┌──────────┐          ┌──────────┐         ┌──────────┐
│  Client  │          │   API    │         │    S3    │
└────┬─────┘          └────┬─────┘         └────┬─────┘
     │                      │                    │
     │  POST /upload/presigned-url               │
     │  {fileName, fileType} │                    │
     ├─────────────────────►│                    │
     │                      │ Pydantic validate  │
     │                      │ Check file type    │
     │                      │ allowed?            │
     │                      │ Generate presigned  │
     │                      │ PUT URL (5min expiry│
     │                      │ Key: uploads/       │
     │                      │  {userId}/{uuid}.ext │
     │                      ├───────────────────►│
     │                      │◄───────────────────│
     │  {uploadUrl,         │                    │
     │   objectKey}         │                    │
     │◄─────────────────────┤                    │
     │                      │                    │
     │  PUT {file}          │                    │
     │  (direct to S3)      │                    │
     ├─────────────────────────────────────────►│
     │                      │                    │
     │  POST /upload/confirm│                    │
     │  {objectKey}         │                    │
     ├─────────────────────►│                    │
     │                      │ Verify object      │
     │                      │ exists in S3       │
     │                      │ Save URL to DB     │
     │  {fileUrl}           │                    │
     │◄─────────────────────┤                    │
     │                      │                    │
```

### 5.3 Attendance Marking Flow

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

### 5.4 Email Notification Flow (Async with Celery)

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  Client  │    │   API    │    │  Redis   │    │  Worker  │    │   SMTP   │
└────┬─────┘    └────┬─────┘    └────┬─────┘    └────┬─────┘    └────┬─────┘
     │                │               │               │               │
     │  POST /register│               │               │               │
     │  event         │               │               │               │
     ├───────────────►│               │               │               │
     │                │ Save reg to DB│               │               │
     │                │ Enqueue email │               │               │
     │                │ task:         │               │               │
     │                │ {type:        │               │               │
     │                │ "registration"│               │               │
     │                │  confirmation"│               │               │
     │                ├──────────────►│               │               │
     │  {success}     │               │               │               │
     │◄───────────────┤               │               │               │
     │                │               │               │               │
     │                │               │ Worker picks  │               │
     │                │               │ up task       │               │
     │                │               ├──────────────►│               │
     │                │               │               │ Compose email │
     │                │               │               │ (Jinja2       │
     │                │               │               │ template +    │
     │                │               │               │ user data)    │
     │                │               │               ├──────────────►│
     │                │               │               │               │
     │                │               │               │◄──────────────│
     │                │               │               │ Mark task done│
     │                │               │◄──────────────│               │
     │                │               │               │               │
     │                │               │ On failure:   │               │
     │                │               │ retry with    │               │
     │                │               │ exponential   │               │
     │                │               │ backoff       │               │
     │                │               │ (max 3 retries)               │
```

---

## 6. Security Architecture

### 6.1 Authentication & Token Management

- **JWT with HS256** (symmetric key from env `JWT_SECRET`). Access tokens expire in **15 minutes**. Refresh tokens expire in **7 days**.
- **Refresh token rotation**: Every time a refresh token is used, the old token is invalidated and a new one issued. If a rotated-out token is ever reused, all refresh tokens for that user are revoked (breach detection).
- **Token blacklist**: On logout, the access token's `jti` is added to Redis with a TTL matching its remaining validity. Every authenticated request checks the blacklist before accepting the token (via FastAPI `Depends(get_current_user)`).
- **Email verification**: New accounts start with `email_verified: False`. A signed email verification link (JWT, 24h expiry) is sent on signup. Protected routes for students check `email_verified` and return 403 if unverified.

### 6.2 Role-Based Access Control (RBAC)

```
Roles (hierarchical):
  admin > teacher > student

FastAPI dependency usage:
  Depends(get_current_user)              // verifies JWT, injects User model
  Depends(require_role('teacher'))       // current_user.role >= 'teacher' (admin also passes)
  Depends(require_role('admin'))         // current_user.role == 'admin'
```

The `require_role` dependency factory accepts a minimum role argument. A dictionary `ROLE_HIERARCHY` maps numeric levels (admin=3, teacher=2, student=1) for comparison. This avoids hard-coded role checks scattered across route handlers.

### 6.3 Input Validation

- Every endpoint uses a **Pydantic v2 schema** that validates request body, query parameters, and path parameters via FastAPI's built-in validation.
- FastAPI automatically returns a 422 response with field-level error details if validation fails — no manual validation middleware needed.
- `model_validator` and `field_validator` decorators enable complex cross-field validation (e.g., end_date > start_date).
- This prevents malformed or malicious input from reaching business logic or the database.

### 6.4 Rate Limiting

| Scope | Limit | Backend |
|---|---|---|
| Authentication (login, signup) | 10 attempts per 15 minutes per IP | Redis sliding window |
| General API | 100 requests per minute per IP | Redis sliding window |
| Attendance marking | 30 requests per minute per user | Redis sliding window |

Rate limit headers are returned: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`.

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

- **File type validation**: Whitelist approach — only specific MIME types are allowed (image/jpeg, image/png, image/webp, application/pdf). Files are validated both by extension and by magic bytes using `python-magic` library.
- **File size limit**: 5MB per file (configurable via `MAX_FILE_SIZE` env).
- **Malware scanning**: Uploaded files are scanned via ClamAV (containerized) before the confirm endpoint accepts the upload. Infected files are deleted from S3.
- **Presigned URL expiry**: Upload URLs expire in 5 minutes, limiting the window for abuse.

### 6.8 Password Hashing

**passlib[bcrypt]** is used with the following parameters:

| Parameter | Value |
|---|---|
| Algorithm | bcrypt (via passlib) |
| Rounds (cost factor) | 12 |
| Salt | Auto-generated 16-byte salt |

bcrypt is the industry standard for password hashing. A cost factor of 12 ensures hashing takes ~250ms on modern hardware, balancing security with user experience. passlib's `CryptContext` provides automatic algorithm migration support if a stronger algorithm is adopted later.

### 6.9 SQL Injection Prevention

All database queries go through **SQLAlchemy 2.0** which uses parameterized queries under the hood. Raw SQL via `text()` is banned — the linter (ruff) enforces this rule.

### 6.10 Audit Logging

All state-mutating operations (create, update, delete, approve, reject) are logged to an `audit_logs` table with: `actor_id`, `action`, `resource_type`, `resource_id`, `old_value` (JSONB), `new_value` (JSONB), `ip_address`, `user_agent`, and `timestamp`. Logs are append-only and immutable.

---

## 7. Caching Strategy

| What | Pattern | TTL | Invalidation Trigger | Rationale |
|---|---|---|---|---|
| Event listings (paginated, filtered) | Cache-aside | 5 minutes | Event created, approved, rejected, updated | Event list is the most frequently read endpoint. 5min TTL balances freshness with cache hit ratio. |
| Single event details | Cache-aside | 5 minutes | Event updated, approved, rejected | Same as listings — read-heavy, low write frequency. |
| User profile (non-sensitive) | Cache-aside | 15 minutes | User updates profile | Profiles change infrequently. Longer TTL is acceptable. |
| Attendance sheet (single event/date) | Cache-aside | 2 minutes | Attendance marked | Attendance is marked live during the event. 2min ensures teachers see recent changes without DB load. |
| Rate limit counters | Direct Redis | 15 minutes | Auto-expiry (sliding window) | Rate limit counts are ephemeral and need no explicit invalidation. |
| Token blacklist | Direct Redis | Until token's `exp` claim | On logout | Blacklist entries must live exactly as long as the token itself. |
| Dashboard stats (admin) | Cache-aside | 10 minutes | Event mutation, registration mutation | Aggregated stats are expensive to compute. Periodic refresh is acceptable. |
| Refresh token hashes | Direct Redis | 7 days | On token rotation or logout | Stored in Redis for fast lookup on refresh; TTL matches token lifetime. |

**Cache-aside (lazy loading) pattern:**
1. Check cache for key `events:list:{hash(query)}`
2. On hit: return cached data
3. On miss: query DB, store in cache, return data
4. On write: delete corresponding cache keys (not update — let next read populate)

---

## 8. Error Handling

### 8.1 Consistent Response Format

Every API response follows this structure:

```python
# Success
{
    "success": true,
    "data": { ... }           # The response payload
}

# Error
{
    "success": false,
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Invalid request data",
        "details": [          # Optional; present for validation errors
            {"field": "email", "message": "Invalid email format"}
        ]
    }
}
```

### 8.2 Exception Class Hierarchy

```
AppHTTPException (base, extends HTTPException)
├── NotFoundException       → 404 — Resource not found
├── UnauthorizedException   → 401 — Missing or invalid authentication
├── ForbiddenException      → 403 — Authenticated but not permitted
├── ValidationException     → 400 — Pydantic validation failure (includes field details)
└── ConflictException       → 409 — Duplicate or state conflict (e.g., already registered)
```

Each exception class accepts a `message` string and optional `details` payload. The `AppHTTPException` base class stores a `status_code` and a machine-readable `code` string (e.g., `"VALIDATION_ERROR"`).

### 8.3 Exception Handlers

FastAPI exception handlers are registered in `main.py` to catch all errors:

1. If the exception is an instance of `AppHTTPException`, use its `status_code` and `code`.
2. If the exception is a `RequestValidationError` (FastAPI's built-in Pydantic validation error), return a `ValidationException` with field-level details.
3. If the exception is from SQLAlchemy (e.g., `IntegrityError`), map known error codes (unique constraint → ConflictException, foreign key → NotFoundException).
4. For unknown errors, log the full stack trace via structlog but return a generic `500 Internal Server Error` without exposing internals.
5. In **development** mode only, attach the stack trace to the response for debugging.

```python
@app.exception_handler(AppHTTPException)
async def app_http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details
            }
        }
    )
```

### 8.4 Unhandled Exceptions & Graceful Shutdown

```python
import asyncio
import signal

async def shutdown(sig, loop):
    logger.info("Received signal %s, shutting down gracefully", sig.name)
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    loop.stop()

loop = asyncio.get_event_loop()
for sig in (signal.SIGTERM, signal.SIGINT):
    loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(shutdown(s, loop)))
```

---

## 9. Logging & Monitoring

### 9.1 Structured Logging with structlog

All logs are output as newline-delimited JSON. In development, logs are pretty-printed via `structlog.dev.ConsoleRenderer`. In production, they are ingested by a log aggregation system (e.g., ELK, Grafana Loki).

```python
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)
```

**Log levels used:** `critical`, `error`, `warning`, `info`, `debug`.

### 9.2 Request Correlation IDs

A custom ASGI middleware generates a unique `request_id` (UUIDv4) per request and attaches it to:

- `request.state.request_id` — accessible in route handlers and dependencies
- `X-Request-ID` response header — returned to the client
- Every log line within the request via structlog's `bind(request_id=...)`

This enables full traceability: given an error reported by a client, search logs for the request ID to see the complete request chain.

### 9.3 Health Check Endpoints

| Endpoint | Purpose | Checks |
|---|---|---|
| `GET /health` | Liveness probe (is the process alive?) | Returns 200 immediately |
| `GET /health/ready` | Readiness probe (can it serve traffic?) | Pings PostgreSQL (`SELECT 1`), Redis (`PING`), returns 200 only if both respond |

These endpoints are **not** rate-limited and **not** authenticated. They are used by Docker's `HEALTHCHECK` and orchestrator (Kubernetes, ECS) probes.

### 9.4 Prometheus Metrics

The `/metrics` endpoint (exposed via `prometheus-fastapi-instrumentator`) exposes:

- `http_requests_total` — counter by method, path, status
- `http_request_duration_seconds` — histogram (50ms, 100ms, 250ms, 500ms, 1s, 2.5s, 5s buckets)
- `db_query_duration_seconds` — histogram (SQLAlchemy event listener wrapping)
- `active_users_total` — gauge (concurrent authenticated users, approximate)
- `celery_task_duration_seconds` — histogram per task type
- `redis_connected` — gauge (1 or 0)

These are scraped by Prometheus and visualized in Grafana dashboards for:
- Error rate by endpoint
- P95/P99 response latency
- Throughput (RPS)
- Database connection pool usage
- Queue depth and age (Celery stalled task alerts)

---

## 10. Deployment Architecture

### 10.1 Docker Multi-Stage Build

```dockerfile
# Stage 1: Dependencies
FROM python:3.12-slim AS deps
WORKDIR /app
RUN pip install --no-cache-dir poetry
COPY pyproject.toml poetry.lock ./
RUN poetry export -f requirements.txt --output requirements.txt --without-hashes
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Production
FROM python:3.12-slim AS production
WORKDIR /app
RUN groupadd --system appgroup && useradd --system --gid appgroup appuser
COPY --from=deps /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY . .
RUN pip install --no-cache-dir -r requirements.txt
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

This produces a slim image (~150MB) with only production dependencies and compiled Python bytecode. No build tools, no dev dependencies.

### 10.2 Docker Compose (Local Development)

```yaml
services:
  app:
    build:
      context: .
      dockerfile: Dockerfile.dev
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    environment:
      - PYTHONDONTWRITEBYTECODE=1
      - DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/acharya
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  celery_worker:
    build:
      context: .
      dockerfile: Dockerfile.dev
    volumes:
      - .:/app
    environment:
      - DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/acharya
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis
    command: celery -A app.workers.celery_app worker --loglevel=info

  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
      POSTGRES_DB: acharya
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user -d acharya"]
      interval: 5s

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redisdata:/data

volumes:
  pgdata:
  redisdata:
```

### 10.3 Environment Configuration

All configuration is loaded from environment variables and validated by pydantic-settings at import time. If any required variable is missing or malformed, the process exits immediately with a clear error message.

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    environment: str = "development"
    port: int = 8000
    database_url: str
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str
    jwt_access_expiry: int = 15  # minutes
    jwt_refresh_expiry: int = 7   # days
    s3_region: str
    s3_bucket: str
    s3_access_key_id: str
    s3_secret_access_key: str
    smtp_host: str
    smtp_port: int = 587
    smtp_user: str
    smtp_pass: str
    cors_origins: list[str] = ["http://localhost:5173"]
    rate_limit_window_ms: int = 60000
    rate_limit_max: int = 100

settings = Settings()
```

| Variable | Required | Description |
|---|---|---|
| `ENVIRONMENT` | Yes | `development`, `production`, or `test` |
| `PORT` | No (default 8000) | HTTP server port |
| `DATABASE_URL` | Yes | PostgreSQL async connection string (`postgresql+asyncpg://...`) |
| `REDIS_URL` | Yes | Redis connection string |
| `JWT_SECRET` | Yes | Symmetric key for signing JWTs (min 32 chars) |
| `JWT_ACCESS_EXPIRY` | No (default 15) | Access token expiry in minutes |
| `JWT_REFRESH_EXPIRY` | No (default 7) | Refresh token expiry in days |
| `S3_REGION` | Yes | AWS region |
| `S3_BUCKET` | Yes | S3 bucket name |
| `S3_ACCESS_KEY_ID` | Yes | AWS access key |
| `S3_SECRET_ACCESS_KEY` | Yes | AWS secret key |
| `SMTP_HOST` | Yes | SMTP server host |
| `SMTP_PORT` | No (default 587) | SMTP server port |
| `SMTP_USER` | Yes | SMTP username |
| `SMTP_PASS` | Yes | SMTP password |
| `CORS_ORIGINS` | No | Comma-separated allowed origins |
| `RATE_LIMIT_WINDOW_MS` | No (default 60000) | Rate limit window in ms |
| `RATE_LIMIT_MAX` | No (default 100) | Max requests per window |

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
| 4 | **Validation** | Pydantic v2 | attrs, msgspec, marshmallow | Pydantic v2's Rust-core engine (pydantic-core) provides 5-50x faster validation than v1. It is the default validation layer for FastAPI, eliminating the need for separate schema definitions. `model_validator` and `field_validator` enable complex validation logic. |
| 5 | **Authentication** | JWT (access + refresh tokens) | Sessions (Starlette session middleware) | JWT is stateless — no database lookup on every request. Works seamlessly with mobile apps and SPAs. Session-based auth requires state storage and cookie management that complicates mobile integration. Refresh token rotation mitigates the inability to revoke JWTs. |
| 6 | **Password Hashing** | passlib[bcrypt] | argon2-cffi, hashlib/PBKDF2 | bcrypt with cost factor 12 is the industry standard; passlib's `CryptContext` supports automatic algorithm migration. Argon2 was considered but bcrypt's broader library support and simpler configuration provide a better DX for this project while maintaining strong security. |
| 7 | **File Uploads** | Presigned S3 URLs | Proxy through server, Multipart direct to API | Presigned URLs allow clients to upload directly to S3 without the server acting as an intermediary. This eliminates the server memory bottleneck (no buffering large files), reduces latency, and lowers bandwidth costs. The server only signs a URL (a lightweight operation). |
| 8 | **Background Jobs** | Celery | In-process asyncio.create_task, plain Redis pub/sub, Huey, Dramatiq | Celery provides persistent queues with built-in retries, rate limiting, scheduled tasks (celery beat), and Flower monitoring UI. In-process tasks have no persistence — if the worker crashes, tasks are lost. Plain Redis pub/sub has no persistence. Huey and Dramatiq have smaller ecosystems. |
| 9 | **Logging** | structlog | logging (stdlib), loguru | structlog provides structured JSON logging with processor pipelines, bound loggers for request-scoped context (correlation IDs), and easy integration with standard library logging. Loguru is simpler but less flexible for production JSON output pipelines. |
| 10 | **API Documentation** | FastAPI auto OpenAPI | Manual OpenAPI, Apispec, Flask-RESTx | FastAPI automatically generates OpenAPI 3.1 spec from route definitions and Pydantic schemas — zero additional code. Interactive docs at `/docs` (Swagger) and `/redoc` (ReDoc) are built in. Manual OpenAPI would duplicate schema definitions. Apispec requires explicit schema annotations. |
| 11 | **Database** | PostgreSQL 16 | MySQL 8, SQLite, MongoDB | PostgreSQL offers superior ACID compliance, advanced indexing (JSONB, GiST for full-text search), and mature replication. MySQL historically has weaker compliance with SQL standards and ACID guarantees in certain configurations. MongoDB's lack of ACID transactions (until very recently) and schema-less nature are inappropriate for a system with strict data integrity requirements. |
| 12 | **Cache** | Redis (redis-py) | In-memory dict, Memcached | Redis is already required for Celery and rate limiting. Using it also for cache eliminates an additional infrastructure dependency. redis-py 5+ includes the `aioredis` functionality natively for async operations. |
| 13 | **Deployment** | Docker + Blue-Green | Serverless (Lambda via Mangum), Single-server manual | Docker ensures environment parity across development, staging, and production. Blue-green deployment provides zero-downtime updates. Serverless via Mangum is possible for FastAPI but unsuitable for a service with long-running Celery workers. |
| 14 | **Migrations** | CI/CD step (alembic upgrade head) | App startup auto-migration, Alembic at entrypoint | Running migrations at startup is convenient but dangerous — multiple instances race to migrate, and migration failures cause application startup failures. Running migrations as an explicit CI/CD step ensures they complete before traffic is routed to the new version. |

(End of file - total 729 lines)
