# Architecture

## Core Sections (Required)

### 1) Architectural Style

- Primary style: Layered modular monolith (API → Service → Model → DB)
- Why this classification: Source is organized into distinct `api/`, `services/`, `models/`, `schemas/`, `core/`, and `middleware/` layers. No microservice, event-driven, or feature-slice decomposition.
- Primary constraints: Async-first (FastAPI + asyncpg + SQLAlchemy async sessions), RBAC with 3 roles (admin > teacher > student), single-college/event-management deployment scope, Supabase PostgreSQL with PgBouncer pooler (`statement_cache_size=0`)

### 2) System Flow

```text
HTTP Request -> Uvicorn ASGI server -> Middleware chain (CORS -> SecurityHeaders -> Timeout -> RateLimit -> RequestID) -> Router (api/v1/) -> Depends (auth deps) -> Service (business logic) -> Model (SQLAlchemy ORM) -> PostgreSQL (Supabase)
```

Flow detail:
1. Request arrives at `uvicorn` ASGI server -> `backend/app/main.py:create_app()`
2. Middleware chain: `CORSMiddleware` -> `SecurityHeadersMiddleware` -> `RequestTimeoutMiddleware` -> rate-limit middleware (auth vs general) -> request-ID middleware
3. Router in `backend/app/api/v1/` matches path, resolves auth dependencies (`get_current_user`, `require_admin`, `require_teacher_or_admin`, `require_student`)
4. Service layer in `backend/app/services/` executes business logic using `AsyncSession` from `get_db()` generator
5. Service uses SQLAlchemy models directly (no repository pattern)
6. Response flows back as JSON — error responses use structured `{"success": false, "error": {...}}` format

### 3) Layer/Module Responsibilities

| Layer or module | Owns | Must not own | Evidence |
|-----------------|------|--------------|----------|
| API Router (api/v1/) | HTTP routing, input validation, response formatting | Business logic, DB queries | `backend/app/api/v1/auth.py` |
| Auth Deps (api/deps.py) | JWT verification, RBAC checks, token blacklist check | DB access, business logic | `backend/app/api/deps.py` |
| Services (services/) | All domain logic, orchestration across models | HTTP concerns, schema validation | `backend/app/services/event.py` |
| Models (models/) | SQLAlchemy table definitions, relationships, enums with lowercase values | Business logic, Pydantic schemas | `backend/app/models/user.py` |
| Schemas (schemas/) | Pydantic request/response shapes, validation rules | ORM mapping, business logic | `backend/app/schemas/auth.py` |
| Core (core/) | DB engine, config (pydantic-settings), security utils (JWT, bcrypt), logging (structlog), exceptions, Redis client singleton | Route handling, business logic | `backend/app/core/database.py` |
| Middleware (middleware/) | Cross-cutting HTTP (rate-limit with Redis/in-memory fallback, security headers, request timeout) | Business logic | `backend/app/middleware/rate_limit.py` |

### 4) Reused Patterns

| Pattern | Where found | Why it exists |
|---------|-------------|---------------|
| AppHTTPException hierarchy | `app/core/exceptions.py` | Structured error codes (`NOT_FOUND`, `UNAUTHORIZED`, `FORBIDDEN`, `VALIDATION_ERROR`, `CONFLICT`) mapped to HTTP status codes |
| Singleton Settings | `app/core/config.py` | Global app configuration via pydantic-settings with env/.env loading |
| Dependency injection (FastAPI Depends) | `app/api/deps.py`, all routers | Async session + auth injection via `get_db()` and `get_current_user()` |
| Repository-free (direct SQLAlchemy in services) | `app/services/*.py` | Services reference `AsyncSession` directly; no repository abstraction layer |
| TimestampMixin | `app/models/base.py` | All models get `id` (UUID PK), `created_at`, `updated_at` via mixin inheritance |
| Factory function (create_app) | `app/main.py` | FastAPI app factory for testability + lifespan management |
| SAEnum with values_callable | `app/models/*.py` | All `SAEnum` columns use `values_callable=lambda obj: [e.value for e in obj]` to match DB lowercase values (Supabase) |
| Rate limiter strategy | `app/middleware/rate_limit.py` | Strategy pattern — `RedisRateLimiter` when Redis available, `InMemoryRateLimiter` as fallback |

### 5) Known Architectural Risks

- **No Repository pattern**: Services directly use SQLAlchemy sessions, making it harder to unit-test business logic in isolation and to swap storage backend
- **In-memory JWT blacklist**: `_blacklisted_tokens` is a module-level `set()` in `app/services/auth.py:16` — blacklist is lost on process restart and not shared across workers
- **Rate limiter state**: `InMemoryRateLimiter` (`middleware/rate_limit.py:12`) uses in-process dict, making it inaccurate under multi-worker deployments — only `RedisRateLimiter` is multi-worker safe
- **Lifespan DB connect failure swallowed**: `main.py:53-57` attempts `engine.connect()` at startup and only logs warning on failure — app starts even with broken DB connection
- **Supabase PgBouncer connection drops**: `statement_cache_size=0` mitigates prepared-statement caching issues, but transient `ConnectionDoesNotExistError` can occur under load (observed during test runs)
- **Sequential dashboard queries**: `app/services/reports.py` executes 8 sequential `db.execute()` calls — can be slow with large datasets

### 6) Evidence

- `backend/app/main.py` (entry point, lifespan, middleware registration, router wiring)
- `backend/app/api/deps.py` (auth DI with blacklist check)
- `backend/app/core/exceptions.py` (error hierarchy)
- `backend/app/models/base.py` (base model + TimestampMixin)
- `backend/app/core/database.py` (async engine with NullPool support)
- `backend/app/middleware/rate_limit.py` (strategy pattern)
- `backend/app/services/auth.py:16` (in-memory blacklist)
- `backend/tests/real_db/conftest.py:30` (statement_cache_size=0 for PgBouncer)
