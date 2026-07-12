# Codebase Structure

## Core Sections (Required)

### 1) Top-Level Map

| Path | Purpose | Evidence |
|------|---------|----------|
| `.github/workflows/` | CI/CD pipeline (GitHub Actions) | `.github/workflows/ci.yml` |
| `backend/` | All application source, tests, and config | Scan output |
| `backend/app/` | FastAPI application package | `backend/app/main.py` |
| `backend/app/api/v1/` | Route handlers — auth, users, events, registrations, attendance, notifications, reports, health | 8 router files in `backend/app/api/v1/` |
| `backend/app/api/deps.py` | Auth dependencies: `get_current_user`, `require_admin`, `require_teacher_or_admin`, `require_student` | `backend/app/api/deps.py` |
| `backend/app/core/` | Infrastructure (config, DB engine, security, logging, exceptions, Redis client) | `backend/app/core/config.py` |
| `backend/app/models/` | SQLAlchemy ORM models (6 files: base, user, event, registration, attendance, notification) | `backend/app/models/user.py` |
| `backend/app/schemas/` | Pydantic v2 request/response schemas (8 files) | `backend/app/schemas/auth.py` |
| `backend/app/services/` | Business logic layer (7 files: auth, user, event, registration, attendance, notification, reports) | `backend/app/services/auth.py` |
| `backend/app/middleware/` | ASGI middleware (rate-limit, security headers, request timeout) | `backend/app/middleware/rate_limit.py` |
| `backend/alembic/` | Database migration scripts (2 versions: 0001_initial, 0002_notifications) | `backend/alembic/versions/` |
| `backend/tests/` | Unit/mock tests (20+ test files) | `backend/tests/conftest.py` |
| `backend/tests/real_db/` | Integration tests against real Supabase (7 files) | `backend/tests/real_db/conftest.py` |
| `backend/scripts/` | Docker entrypoint + seed data scripts | `backend/scripts/entrypoint.sh` |
| `docs/` | Architecture docs, API spec, DB schema, plans | `docs/architecture.md` |

### 2) Entry Points

- Main runtime entry: `backend/app/main.py:96` — `create_app()` FastAPI app factory
- Module-level convenience: `backend/app/main.py:176` — `app = create_app()` for `uvicorn app.main:app`
- Server start: `uvicorn app.main:create_app --factory` (or `uvicorn app.main:app`)
- Secondary: `backend/scripts/seed.py` (data seeder), `backend/scripts/entrypoint.sh` (Docker, runs `alembic upgrade head` then starts uvicorn)
- ASGI server: uvicorn 0.34.0

### 3) Module Boundaries

| Boundary | What belongs here | What must not be here |
|----------|-------------------|------------------------|
| `app/api/v1/` | Route handlers, HTTP concerns, request validation | Business logic, DB queries |
| `app/api/deps.py` | Auth dependency injection (JWT verify, RBAC) | Business logic |
| `app/services/` | Business logic, orchestration across models | HTTP concerns, schema validation |
| `app/models/` | SQLAlchemy ORM table definitions, relationships, enums | Business logic, Pydantic schemas |
| `app/schemas/` | Pydantic v2 request/response shapes | Business logic, ORM models |
| `app/core/` | Config, DB engine, security utils, logging setup, exceptions | Route handlers, business logic |
| `app/middleware/` | Cross-cutting HTTP concerns | Business logic, data access |

### 4) Naming and Organization Rules

- File naming pattern: snake_case for Python files (e.g., `rate_limit.py`, `logging_config.py`)
- Directory organization pattern: Layer-based (api/core/models/services/schemas/middleware)
- Import aliasing or path conventions: Absolute imports from `app.` package (e.g., `from app.core.config import settings`)
- Router registration: Each `api/v1/*.py` file defines a `router = APIRouter()` which is imported and included in `app/main.py:create_app()`

### 5) Evidence

- Scan output directory tree
- `backend/app/main.py` (entry point, router registration, middleware wiring)
- `backend/app/core/database.py` (DB engine + session)
- `backend/tests/conftest.py` (test app fixture)
- `backend/tests/real_db/conftest.py` (real DB test setup)
