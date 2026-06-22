# Codebase Concerns

## Core Sections (Required)

### 1) Top Risks (Prioritized)

| Severity | Concern | Evidence | Impact | Suggested action |
|----------|---------|----------|--------|------------------|
| ~~High~~ **FIXED** | **CI pipeline could not run tests** — `fakeredis` and `testcontainers` not in `requirements.txt` | `backend/requirements.txt:20-21` (now added) | `pytest -v` in CI no longer fails during collection | ✅ Added `fakeredis[lua]>=2.0.0` and `testcontainers[postgres,redis]>=4.0.0` |
| ~~High~~ **FIXED** | **No PostgreSQL service in CI** — `DATABASE_URL` pointed to `localhost:5432` with no Postgres container | `.github/workflows/ci.yml:17-30` (services block added) | CI now has a real Postgres available | ✅ Added `services.postgres` with `postgres:16-alpine`, proper health checks, and port mapping |
| Low | **Unused `celery` dependency** removed from `requirements.txt` | `backend/requirements.txt` (celery removed) | Cleaner dependency list | ✅ Removed `celery[redis]>=5.4.0` — was never imported in any source or test file |
| Medium | **In-memory rate limiter is not multi-worker safe** | `backend/app/middleware/rate_limit.py:12-23` | Under multiple uvicorn workers, each process has its own in-memory counter — rate limit is per-worker, not global | Always use Redis-backed limiter in production; document requirement |
| Medium | **Silent DB failure on startup** — lifespan catches and logs but does not prevent app from starting | `backend/app/main.py:53-57` | App can start with a broken database connection; first user request gets a connection error instead of a clear health-check failure | Make DB health check a startup hard dependency or expose status via health endpoint |

### 2) Technical Debt

| Debt item | Why it exists | Where | Risk if ignored | Suggested fix |
|-----------|---------------|-------|-----------------|---------------|
| No linting/formatter | Not configured in project | No `.flake8`, `.pylintrc`, `.ruff.toml`, or similar | Code style drifts; CI has no style checks | Add ruff or flake8 + black; add to CI |
| No pre-commit hooks | Not configured | No `.pre-commit-config.yaml` | Commits can include secrets, debug code, or unformatted files | Add pre-commit with ruff, secrets scanner |
| `_blacklisted_tokens` is in-memory set | JWT token blacklist uses module-level `set()` | `backend/app/services/auth.py:16` | Blacklist lost on process restart; not shared across workers | Store blacklist in Redis |
| Repository-free services | Services directly use SQLAlchemy sessions | `backend/app/services/*.py` | Harder to unit-test and swap storage backend | Consider introducing repository abstractions for complex queries |
| No health endpoint DB check | Health endpoint (`GET /health`) does not verify DB connectivity | `backend/tests/test_health.py` (only checks HTTP 200) | Health endpoint reports "ok" even when database is down | Add DB ping + Redis ping to health check |

### 3) Security Concerns

| Risk | OWASP category (if applicable) | Evidence | Current mitigation | Gap |
|------|--------------------------------|----------|--------------------|-----|
| JWT blacklist in memory | N/A | `backend/app/services/auth.py:16` | None cross-worker | No distributed token revocation |
| No rate limiting on health endpoint | N/A | `backend/app/main.py:139` | Rate limiter skips health path | Health endpoint is unauthenticated and unrate-limited |
| bcrypt rounds not configurable | N/A | `backend/app/core/security.py:53` (`bcrypt.gensalt()` uses default) | Default rounds (likely 12) | Hardcoded — no env var to adjust cost factor |

### 4) Performance and Scaling Concerns

| Concern | Evidence | Current symptom | Scaling risk | Suggested improvement |
|---------|----------|-----------------|-------------|-----------------------|
| Sequential queries in dashboard | `backend/app/services/reports.py` (8 sequential `db.execute` calls) | Slow dashboard load with large datasets | High — each async query is round-trip to Postgres | Batch queries into fewer SQL statements or use `asyncio.gather` |
| No connection pooling limits for async | `backend/app/core/database.py:17` uses `NullPool` when `ASYNC_NULLPOOL=1` | Dev/test only — production uses default pool | Low in production (uses pooling) | Ensure production runs with pool_size=5 as configured |

### 5) Fragile/High-Churn Areas

| Area | Why fragile | Churn signal | Safe change strategy |
|------|-------------|-------------|----------------------|
| `backend/app/main.py` | Central wiring of lifespan, middleware, routers, rate limiters | 11 commits in last 90 days (highest churn) | Add tests for each middleware/router registration |
| `backend/tests/test_notifications.py` | 7 commits — notification module is newest and rapidly evolving | 7 commits | Test inline with each feature addition |
| `backend/app/api/deps.py` | Auth deps used by all protected routes — any breakage cascades | 4 commits | Maintain auth unit tests |

### 6) `[ASK USER]` Questions

1. [ASK USER] Which CI provider and where can I see the failing PR test output (URL)?
2. [ASK USER] Should `fakeredis` and `testcontainers` be moved to `[dependency-groups] dev` in `pyproject.toml` or added to `requirements.txt`?
3. [ASK USER] Is there a linter/formatter preference (ruff, black, flake8) to add to the project?
4. [ASK USER] Should `celery` (listed in requirements but no usage found in code) be removed?
5. [ASK USER] What is the team's preferred approach for the in-memory JWT blacklist — Redis-based or stateless token approach?

### 7) Evidence

- `backend/requirements.txt` (missing test deps)
- `.github/workflows/ci.yml` (CI config, missing Postgres service)
- Scan output: git log (high-churn files)
- `backend/app/middleware/rate_limit.py:12` (in-memory limiter)
- `backend/app/services/auth.py:16` (in-memory blacklist)
