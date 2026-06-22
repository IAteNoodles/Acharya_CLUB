# Coding Conventions

## Core Sections (Required)

### 1) Naming Rules

| Item | Rule | Example | Evidence |
|------|------|---------|----------|
| Files | snake_case | `rate_limit.py`, `logging_config.py` | `backend/app/middleware/rate_limit.py` |
| Functions/methods | snake_case | `create_app`, `get_current_user` | `backend/app/main.py:96` |
| Types/interfaces | PascalCase | `AppHTTPException`, `TimestampMixin` | `backend/app/core/exceptions.py`, `backend/app/models/base.py` |
| Constants/env vars | UPPER_SNAKE_CASE (env) | `JWT_SECRET`, `DATABASE_URL` | `backend/app/core/config.py` |

### 2) Formatting and Linting

- Formatter: [TODO] — No formatter config detected
- Linter: [TODO] — No linter config detected
- Most relevant enforced rules: No linting/formatter configuration found
- Run commands: None configured

### 3) Import and Module Conventions

- Import grouping/order: Standard Python (stdlib → third-party → local `app.`); no enforced grouping rules
- Alias vs relative import policy: Absolute imports from `app.` package (e.g., `from app.core.config import settings`)
- Public exports/barrel policy: `app/models/__init__.py` and `app/schemas/__init__.py` re-export key types; no explicit `__all__` detected

### 4) Error and Logging Conventions

- Error strategy by layer: Custom `AppHTTPException` hierarchy (`exceptions.py`) with `error_code` + `detail`; caught by registered exception handlers that return `{"success": false, "error": {"code": ..., "message": ...}}` JSON. Unhandled exceptions return 500 with generic message.
- Logging style and required context fields: structlog with JSON renderer, ISO timestamps, log level; request ID added via middleware context vars
- Sensitive-data redaction rules: [TODO] — no explicit redaction detected

### 5) Testing Conventions

- Test file naming/location rule: `tests/test_<module>.py` for unit/mock tests; `tests/real_db/test_<module>.py` for real DB tests
- Mocking strategy norm: `unittest.mock.AsyncMock` + `MagicMock` for service-level tests; FastAPI `dependency_overrides` for API-level tests
- Coverage expectation: [TODO] — no coverage threshold configured

### 6) Evidence

- `backend/app/core/exceptions.py` (error patterns)
- `backend/app/core/logging_config.py` (logging setup)
- `backend/tests/conftest.py` (test setup)
- `backend/pyproject.toml` (pytest config)
