# Codebase Structure

## Core Sections (Required)

### 1) Top-Level Map

| Path | Purpose | Evidence |
|------|---------|----------|
| `.github/workflows/` | CI/CD pipeline (GitHub Actions) | `.github/workflows/ci.yml` |
| `backend/` | All application source, tests, and config | Scan output |
| `backend/app/` | FastAPI application package | `backend/app/main.py` |
| `backend/app/api/` | Route handlers + auth dependencies | `backend/app/api/v1/` files |
| `backend/app/core/` | Infrastructure (config, DB, security, logging, exceptions) | `backend/app/core/config.py` |
| `backend/app/models/` | SQLAlchemy ORM models | `backend/app/models/` |
| `backend/app/schemas/` | Pydantic v2 request/response schemas | `backend/app/schemas/` |
| `backend/app/services/` | Business logic layer | `backend/app/services/auth.py` |
| `backend/app/middleware/` | ASGI middleware (rate-limit, security, timeout) | `backend/app/middleware/` |
| `backend/alembic/` | Database migration scripts | `backend/alembic/versions/` |
| `backend/tests/` | Unit/mock tests + real-db tests + E2E | `backend/tests/conftest.py` |
| `docker-compose.yml` | Dev Docker Compose | `backend/docker-compose.yml` |
| `docs/` | Architecture docs, API spec, DB schema, plans | `docs/architecture.md` |

### 2) Entry Points

- Main runtime entry: `backend/app/main.py:create_app()` — FastAPI app factory
- Secondary entry points: `backend/scripts/seed.py` (data seeder), `backend/scripts/entrypoint.sh` (Docker entrypoint)
- How entry is selected: `uvicorn app.main:create_app --factory` for server; Docker entrypoint runs `alembic upgrade head` before starting

### 3) Module Boundaries

| Boundary | What belongs here | What must not be here |
|----------|-------------------|------------------------|
| `app/api/` | Route handlers, HTTP concerns, auth deps | Business logic, DB queries |
| `app/services/` | Business logic, orchestration | HTTP concerns, DB schema |
| `app/models/` | SQLAlchemy ORM definitions | Business logic, Pydantic schemas |
| `app/schemas/` | Pydantic v2 request/response models | Business logic, ORM models |
| `app/core/` | Config, DB engine, security, logging, exceptions | Route handlers, business logic |
| `app/middleware/` | Cross-cutting HTTP concerns | Business logic, data access |

### 4) Naming and Organization Rules

- File naming pattern: snake_case for Python files (e.g., `auth.py`, `rate_limit.py`)
- Directory organization pattern: Layer-based (api/core/models/services/schemas)
- Import aliasing or path conventions: Standard Python absolute imports from `app.` (e.g., `from app.core.config import settings`)

### 5) Evidence

- Scan output directory tree
- `backend/app/main.py`
- `backend/app/core/database.py`
- `backend/tests/conftest.py`
