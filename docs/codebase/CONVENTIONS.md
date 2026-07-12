# Coding Conventions

## Core Sections (Required)

### 1) Naming Rules

| Item | Rule | Example | Evidence |
|------|------|---------|----------|
| Files | snake_case | `rate_limit.py`, `logging_config.py`, `test_auth.py` | `backend/app/middleware/rate_limit.py` |
| Functions/methods | snake_case | `create_app`, `get_current_user`, `verify_token`, `hash_password` | `backend/app/main.py:96` |
| Classes/types | PascalCase | `AppHTTPException`, `TimestampMixin`, `User`, `Event`, `RedisRateLimiter` | `backend/app/core/exceptions.py`, `backend/app/models/user.py` |
| Enums | PascalCase | `Role`, `UserStatus`, `EventType`, `EventStatus` | `backend/app/models/user.py:8` |
| Enum values | lowercase | `"student"`, `"active"`, `"workshop"`, `"pending"` | `backend/app/models/user.py:9` |
| Config env vars | UPPER_SNAKE_CASE | `JWT_SECRET`, `DATABASE_URL`, `DB_PASSWORD` | `backend/app/core/config.py` |
| Modules/directories | snake_case | `api/`, `v1/`, `core/`, `middleware/` | Directory tree |
| Private module-level | `_` prefix | `_blacklisted_tokens`, `_redis_instance`, `_is_upstash()` | `backend/app/services/auth.py:16` |

### 2) Formatting and Linting

- Formatter: None configured
- Linter: None configured — no `.flake8`, `.pylintrc`, `.ruff.toml`, or ruff section in `pyproject.toml`
- Most relevant enforced rules: None
- Run commands: None configured
- Note: This is a known gap tagged in `CONCERNS.md`

### 3) Import and Module Conventions

- Import grouping/order: Standard Python (stdlib → third-party → local `app.`); no enforced grouping rules
- Alias vs relative import policy: Absolute imports from `app.` package (e.g., `from app.core.config import settings`, never `from ..core import config`)
- Public exports/barrel policy: `app/models/__init__.py` and `app/schemas/__init__.py` re-export key types; no explicit `__all__` detected
- Lazy imports visible in services: `from fastapi import HTTPException` is done inline within functions (e.g., `backend/app/services/auth.py:27`)

### 4) Error and Logging Conventions

- Error strategy by layer: Custom `AppHTTPException` hierarchy (`exceptions.py`) with `error_code` + `detail`; caught by registered exception handlers that return `{"success": false, "error": {"code": ..., "message": ...}}` JSON. Unhandled exceptions return 500 with generic `"INTERNAL_ERROR"`.
- Logging style: structlog with `JSONRenderer()` — all logs output as newline-delimited JSON with ISO timestamps and log levels
- Request context: Request-ID middleware generates UUIDv4 per request, bound via `structlog.contextvars.bound_contextvars(request_id=...)` and returned as `X-Request-ID` header
- Sensitive-data redaction rules: No explicit redaction detected; passwords are hashed before logging/db via bcrypt

### 5) Testing Conventions

- Test file naming/location rule: `tests/test_<module>.py` for unit/mock tests; `tests/real_db/test_<module>.py` for real DB tests against Supabase; `tests/test_e2e_workflows.py` for E2E (testcontainers)
- Mocking strategy norm: `unittest.mock.AsyncMock` + `MagicMock` for service-level tests; FastAPI `dependency_overrides` for API-level tests with mock auth users
- Real DB isolation: Transaction-per-test — each test gets a fresh `AsyncSession` with `begin()/rollback()` to isolate changes
- E2E isolation: Testcontainers spin up fresh PostgreSQL + Redis containers per session; schema created via sync SQLAlchemy engine
- Coverage expectation: No threshold configured, but CI runs `--cov=app --cov-report=term-missing`
- Async loop scope: `asyncio_default_fixture_loop_scope = "function"` in `pyproject.toml`

### 6) Evidence

- `backend/app/core/exceptions.py` (error patterns)
- `backend/app/core/logging_config.py` (logging setup with JSONRenderer)
- `backend/app/core/security.py` (JWT + bcrypt patterns)
- `backend/tests/conftest.py` (test app fixture)
- `backend/tests/real_db/conftest.py` (transaction-per-test pattern)
- `backend/tests/test_e2e_workflows.py` (testcontainers pattern)
- `backend/pyproject.toml` (pytest config, no linter section)
- `backend/app/main.py` (request-ID middleware)
