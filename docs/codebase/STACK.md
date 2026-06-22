# Technology Stack

## Core Sections (Required)

### 1) Runtime Summary

| Area | Value | Evidence |
|------|-------|----------|
| Primary language | Python 3.12+ | `backend/pyproject.toml:5` |
| Runtime + version | CPython 3.12+ (CI: 3.12, Docker: 3.13-alpine) | `.github/workflows/ci.yml:10`, `backend/Dockerfile:2` |
| Package manager | pip (with requirements.txt) + UV lockfile | `backend/requirements.txt`, `backend/uv.lock` |
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
| PyJWT | >=2.13.0 | JWT auth | `backend/requirements.txt:8` |
| bcrypt | >=4.2.0 | Password hashing | `backend/requirements.txt:9` |
| redis[hiredis] | >=5.2.1 | Redis client (rate limiting) | `backend/requirements.txt:10` |
| structlog | >=24.4.0 | Structured JSON logging | `backend/requirements.txt:12` |
| upstash-redis | >=1.7.0 | Upstash REST-based Redis | `backend/requirements.txt:13` |
| python-multipart | >=0.0.19 | Form parsing | `backend/requirements.txt:14` |

### 3) Development Toolchain

| Tool | Purpose | Evidence |
|------|---------|----------|
| pytest | Test runner | `backend/requirements.txt:17` |
| pytest-asyncio | Async test support | `backend/requirements.txt:18` |
| httpx | HTTP client for API tests | `backend/requirements.txt:19` |
| pytest-cov | Coverage reporting | `backend/requirements.txt:20` |
| testcontainers | Docker containers for real DB/E2E tests | `backend/tests/real_db/conftest.py:10` |
| fakeredis | Fake Redis for unit tests | `backend/tests/test_rate_limit.py:2` |

### 4) Key Commands

```bash
pip install -r requirements.txt
alembic upgrade head
pytest -v
# No lint/formatter command configured
```

### 5) Environment and Config

- Config sources: `backend/.env`, environment variables (pydantic-settings)
- Required env vars: `JWT_SECRET` (min 32 chars), `DATABASE_URL` (or `DB_PASSWORD` + components)
- Deployment/runtime constraints: Requires PostgreSQL 16+, Redis 7 (optional, in-memory fallback), Docker for containerized deployment

### 6) Evidence

- `backend/pyproject.toml`
- `backend/requirements.txt`
- `backend/Dockerfile`
- `.github/workflows/ci.yml`
