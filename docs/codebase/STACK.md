# Technology Stack

## Core Sections (Required)

### 1) Runtime Summary

| Area | Value | Evidence |
|------|-------|----------|
| Primary language | Python 3.12+ | `backend/pyproject.toml:5` |
| Runtime + version | CPython 3.12 (CI) / 3.13 (Docker: `python:3.13-alpine`) | `.github/workflows/ci.yml:19`, `backend/Dockerfile:2` |
| Package manager | pip (requirements.txt) + UV lockfile | `backend/requirements.txt`, `backend/uv.lock` |
| Module/build system | setuptools (pyproject.toml) | `backend/pyproject.toml:11-12` |

### 2) Production Frameworks and Dependencies

| Dependency | Version | Role in system | Evidence |
|------------|---------|----------------|----------|
| FastAPI | >=0.138.0,<0.139.0 | Web framework (REST API) | `backend/requirements.txt:2` |
| Uvicorn | 0.34.0 | ASGI server | `backend/requirements.txt:3` |
| SQLAlchemy | >=2.0.36 | Async ORM | `backend/requirements.txt:4` |
| asyncpg | >=0.30.0 | PostgreSQL async driver | `backend/requirements.txt:5` |
| Alembic | >=1.14.0 | DB migrations | `backend/requirements.txt:6` |
| pydantic-settings | >=2.7.0 | Config management | `backend/requirements.txt:7` |
| PyJWT[crypto] | >=2.13.0 | JWT auth | `backend/requirements.txt:8` |
| bcrypt | >=4.2.0 | Password hashing | `backend/requirements.txt:9` |
| redis[hiredis] | >=5.2.1 | Redis client (rate limiting, caching) | `backend/requirements.txt:10` |
| structlog | >=24.4.0 | Structured JSON logging | `backend/requirements.txt:11` |
| upstash-redis | >=1.7.0 | REST-based Redis (no TCP) | `backend/requirements.txt:12` |
| python-multipart | >=0.0.19 | Form parsing (login, signup) | `backend/requirements.txt:13` |

### 3) Development Toolchain

| Tool | Purpose | Evidence |
|------|---------|----------|
| pytest | Test runner | `backend/requirements.txt:16` |
| pytest-asyncio | Async test support | `backend/requirements.txt:17` |
| httpx | HTTP client for API tests | `backend/requirements.txt:18` |
| pytest-cov | Coverage reporting | `backend/requirements.txt:19` |
| fakeredis[lua] | Fake Redis for unit tests | `backend/requirements.txt:20` |
| testcontainers[postgres,redis] | Docker containers for E2E tests | `backend/requirements.txt:21` |
| psycopg2-binary | Sync SQLAlchemy driver (testcontainers schema setup in E2E) | `backend/requirements.txt:22` |

### 4) Key Commands

```bash
pip install -r requirements.txt
alembic upgrade head
pytest -v                                     # default (excludes e2e)
pytest -m e2e -v                              # with Docker
pytest --cov=app --cov-report=term-missing     # with coverage
```

### 5) Environment and Config

- Config sources: `backend/.env`, environment variables (pydantic-settings)
- Required env vars: `DB_PASSWORD` or `DATABASE_URL` (Supabase); `JWT_SECRET` auto-generated in development
- Deployment/runtime constraints: Requires PostgreSQL 16+ (Supabase), Redis 7 optional (in-memory fallback), Docker for E2E tests
- Supabase defaults: `DB_USER`, `DB_HOST`, `DB_PORT`, `DB_NAME` are hardcoded in config.py for `postgres.qwouxrnnwmkotkwraqme`

### 6) Evidence

- `backend/pyproject.toml`
- `backend/requirements.txt`
- `backend/Dockerfile`
- `.github/workflows/ci.yml`
- `backend/app/core/config.py`
