# Testing Patterns

## Core Sections (Required)

### 1) Test Stack and Commands

- Primary test framework: pytest 8.3.4+ (requirements.txt:17)
- Assertion/mocking tools: `unittest.mock` (AsyncMock, MagicMock), `httpx.AsyncClient` + `ASGITransport`, `FastAPI.dependency_overrides`, `fakeredis`, `testcontainers`
- Commands:

```bash
pytest -v                                          # default (excludes E2E)
pytest -v -m "not real_db and not e2e"             # unit/mock only
pytest -v tests/real_db/                           # real DB only
pytest -v -m ""                                    # all tests including E2E
pytest --cov=app --cov-report=term-missing          # with coverage
```

### 2) Test Layout

- Test file placement pattern: All tests in `backend/tests/` — separate `real_db/` subdirectory for integration tests
- Naming convention: `test_<module>.py` (e.g., `test_auth.py`, `test_events.py`)
- Setup files and where they run: `backend/tests/conftest.py` (app fixture → `create_app()`), `backend/tests/real_db/conftest.py` (PostgresContainer fixtures)

### 3) Test Scope Matrix

| Scope | Covered? | Typical target | Notes |
|-------|----------|----------------|-------|
| Unit | Yes | Service functions, schema validation, security utils | Mocked DB session; no external dependencies |
| Integration | Yes | API endpoints with mocked services | FastAPI `dependency_overrides` + `patch` on service layer |
| Real DB | Yes | Repository-like data access via testcontainers | `testcontainers.PostgresContainer` — requires Docker |
| E2E | Yes | Full user journeys (signup → login → create event → register → attend) | `testcontainers` for Postgres + Redis; marked `@pytest.mark.e2e` |

### 4) Mocking and Isolation Strategy

- Main mocking approach: `unittest.mock.AsyncMock` for async DB sessions; `unittest.mock.patch` to replace service functions at module level; FastAPI `dependency_overrides` to inject mock auth users
- Isolation guarantees: Real DB tests use rollback-per-test (transaction wraps each test). Unit tests create fresh mock objects per test.
- Common failure mode in tests: Missing test dependencies (`fakeredis`, `testcontainers`) in requirements.txt cause module import errors during test collection.

### 5) Coverage and Quality Signals

- Coverage tool + threshold: `pytest-cov` available but no threshold configured
- Current reported coverage: [TODO] — not measured in CI
- Known gaps/flaky areas:
  - `test_database.py` connects to whatever `DATABASE_URL` points to — CI now provides a Postgres service
  - `real_db` tests require Docker — fail if Docker not available locally; CI runners have Docker

### 6) Evidence

- `backend/pyproject.toml` (pytest config, markers)
- `backend/tests/conftest.py` (app fixture)
- `backend/tests/real_db/conftest.py` (PostgresContainer setup)
- `backend/tests/test_e2e_workflows.py` (E2E test pattern)
- `backend/requirements.txt` (missing fakeredis, testcontainers)
