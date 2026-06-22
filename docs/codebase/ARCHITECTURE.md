# Architecture

## Core Sections (Required)

### 1) Architectural Style

- Primary style: Layered modular monolith (API → Service → Model → DB)
- Why this classification: Source is organized into distinct `api/`, `services/`, `models/`, `schemas/`, `core/`, and `middleware/` layers. No microservice, event-driven, or feature-slice decomposition.
- Primary constraints: Async-first (FastAPI + asyncpg + SQLAlchemy async), RBAC (3-role auth), single-college deployment scope

### 2) System Flow

```text
HTTP Request -> Middleware (CORS, Security Headers, Timeout, Rate Limit) -> Router (api/v1/) -> Depends (auth deps) -> Service (business logic) -> Model (SQLAlchemy ORM) -> PostgreSQL
```

Flow detail:
1. Request arrives at `uvicorn` ASGI server -> `app.main:create_app()`
2. Middleware chain: CORSMiddleware -> SecurityHeadersMiddleware -> RequestTimeoutMiddleware -> Rate-limit middleware -> Request-ID middleware
3. Router in `app/api/v1/` matches path, resolves auth dependencies (`get_current_user`, `require_admin`, etc.)
4. Service layer in `app/services/` executes business logic
5. Service uses `AsyncSession` from `app/core/database.py:get_db()` to query/update via SQLAlchemy models
6. Response flows back through the middleware chain as JSON

### 3) Layer/Module Responsibilities

| Layer or module | Owns | Must not own | Evidence |
|-----------------|------|--------------|----------|
| API Router | HTTP routing, input validation, response formatting, auth deps | Business logic, DB queries | `backend/app/api/v1/auth.py` |
| Auth Deps | JWT verification, RBAC checks | DB access, business logic | `backend/app/api/deps.py` |
| Services | All domain logic, orchestration | HTTP concerns, schema validation | `backend/app/services/event.py` |
| Models | SQLAlchemy table definitions, relationships, enums | Business logic | `backend/app/models/user.py` |
| Schemas | Pydantic request/response shapes, validation rules | ORM mapping, business logic | `backend/app/schemas/auth.py` |
| Core | DB engine, config, security utils, logging, exceptions | Route handling, business logic | `backend/app/core/database.py` |
| Middleware | Cross-cutting HTTP (rate-limit, security headers, timeout) | Business logic | `backend/app/middleware/rate_limit.py` |

### 4) Reused Patterns

| Pattern | Where found | Why it exists |
|---------|-------------|---------------|
| AppHTTPException hierarchy | `app/core/exceptions.py` | Structured error codes across the API |
| Singleton Settings | `app/core/config.py` | Global app configuration via pydantic-settings |
| Dependency injection (FastAPI Depends) | `app/api/deps.py`, all routers | Async session + auth injection |
| Repository-free (direct SQLAlchemy in services) | `app/services/*.py` | Keeps things simple for single-college scope |
| TimestampMixin | `app/models/base.py` | Auto `id`/`created_at`/`updated_at` on all models |
| Factory function (create_app) | `app/main.py` | FastAPI app factory for testability + lifespan management |

### 5) Known Architectural Risks

- **No Repository pattern**: Services directly use SQLAlchemy sessions, making it harder to mock/test business logic in isolation and to swap databases later
- **Lifespan DB connect on startup**: `main.py:54` attempts `engine.connect()` at startup and swallows failures. Silent DB failures may go undetected until a request fails
- **Rate limiter state**: `InMemoryRateLimiter` uses in-process dict (`middleware/rate_limit.py:12`), making it inaccurate under multi-worker deployments

### 6) Evidence

- `backend/app/main.py` (entry point, lifespan, middleware registration)
- `backend/app/api/deps.py` (auth DI)
- `backend/app/core/exceptions.py` (error hierarchy)
- `backend/app/models/base.py` (base model pattern)
