# Testing Patterns

## Core Sections (Required)

### 1) Test Stack and Commands

- Primary test framework: pytest 8.3.4+
- Assertion/mocking tools: `unittest.mock` (`AsyncMock`, `MagicMock`, `patch`), `httpx.AsyncClient` + `ASGITransport`, FastAPI `dependency_overrides`, `fakeredis`, `testcontainers` (E2E only)
- Commands:

```bash
pytest -v                                          # default (excludes E2E, 339 tests collected, 6 deselected)
pytest -m e2e -v                                   # E2E only — requires Docker
pytest tests/real_db/ -v                           # real Supabase tests only
pytest --cov=app --cov-report=term-missing          # with coverage
```

### 2) Test Layout

| Path | Count | Purpose | Dependencies |
|------|-------|---------|-------------|
| `tests/` | ~20 files | Unit/mock tests | None (mocked DB/Redis) |
| `tests/real_db/` | 7 files | Integration tests against real Supabase | Supabase `.env` credentials |
| `tests/test_e2e_workflows.py` | 1 file (6 tests) | Full-stack E2E via testcontainers | Docker (Postgres + Redis containers) |

- Test file naming convention: `test_<module>.py` (e.g., `test_auth.py`, `test_events.py`)
- Setup files: `backend/tests/conftest.py` (app fixture via `create_app()`), `backend/tests/real_db/conftest.py` (Supabase engine + user fixtures)
- Async loop scope: `asyncio_default_fixture_loop_scope = "function"` in `pyproject.toml`

### 3) Test Scope Matrix

| Scope | Covered? | Typical target | Implementation |
|-------|----------|----------------|----------------|
| Unit | Yes | Schema validation (`test_auth_schemas.py`), security utils (`test_security.py`), config validation (`test_config.py`), exception handlers (`test_exceptions.py`), rate limiter (`test_rate_limit.py`), Redis (`test_redis.py`), logging (`test_logging_config.py`), timeout (`test_timeout.py`) | Pure function tests; no DB or HTTP |
| Service/Mock | Yes | Service functions with mocked DB session | `AsyncMock` session + `MagicMock` on model instances |
| API/Integration | Yes | Endpoint behavior with mocked services | FastAPI `TestClient` + `dependency_overrides` for auth |
| Real DB | Yes | Data access against real Supabase | Direct async engine + rollback-per-test isolation |
| E2E | Yes | Full user journeys (signup→login→create event→register→attend) | `testcontainers.PostgresContainer` + `RedisContainer`, session-scoped |

### 4) Mocking and Isolation Strategy

- **Unit/service tests**: `unittest.mock.patch` replaces `get_db` to inject mock `AsyncSession`. Model instances are `MagicMock` with awaited async methods.
- **API tests**: FastAPI `app.dependency_overrides[get_current_user]` injects mock user payloads. Service functions are patched at module level.
- **Real DB tests**: Transaction-per-test — `async_engine.connect()` → `conn.begin()` → `AsyncSession(bind=conn)` → test runs → `trans.rollback()` → `conn.close()`. Each test gets clean state.
- **E2E tests**: Session-scoped fixtures spin up Docker containers; schema created via sync SQLAlchemy engine; env vars overridden to point at containers.
- **Redis mocking**: `fakeredis` provides in-memory Redis for rate limiter tests without needing a real Redis server.

### 5) Coverage and Quality Signals

- Coverage tool: `pytest-cov`
- CI runs: `pytest --cov=app --cov-report=term-missing` (no threshold configured)
- Current coverage: ~97% (documented in recent commit `b6ad357`)
- Known gaps:
  - `real_db` tests require Supabase credentials in `.env` — fail fast if database is unreachable (no skip behavior)
  - `E2E` tests require Docker — error if Docker not running
  - `test_database.py` connects to whatever `DATABASE_URL` points to

### 6) Markers

| Marker | Purpose | Defined in |
|--------|---------|------------|
| `e2e` | End-to-end tests (require Docker) | `pyproject.toml:30` |
| `slow` | Slow tests (deselect with `-m "not slow"`) | `pyproject.toml:31` |
| Default `addopts` | `-m 'not e2e'` — excludes E2E from default run | `pyproject.toml:35` |

### 7) Evidence

- `backend/pyproject.toml` (pytest config, markers, addopts)
- `backend/tests/conftest.py` (app fixture)
- `backend/tests/real_db/conftest.py` (direct Supabase connection; no testcontainers)
- `backend/tests/test_e2e_workflows.py` (testcontainers E2E pattern)
- `backend/requirements.txt` (test dependencies: fakeredis, testcontainers, psycopg2-binary)
- `.github/workflows/ci.yml` (CI test command with coverage)
