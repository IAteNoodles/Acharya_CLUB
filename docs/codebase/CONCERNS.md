# Codebase Concerns

## Core Sections (Required)

### 1) Top Risks (Prioritized)

| Severity | Concern | Evidence | Impact | Suggested action |
|----------|---------|----------|--------|------------------|
| ~~High~~ **FIXED** | **In-memory JWT blacklist** | `backend/app/services/auth.py` — migrated to Redis | ✅ Blacklist persists across workers/restarts with Redis | ✅ `_is_blacklisted` / `_add_to_blacklist` with in-memory fallback |
| ~~Medium~~ **FIXED** | **Sequential dashboard queries** | `backend/app/services/reports.py` — migrated to `asyncio.gather` | ✅ All 8 queries run concurrently | ✅ `asyncio.gather` replaces sequential awaits |
| Medium | **In-memory rate limiter is not multi-worker safe** | `backend/app/middleware/rate_limit.py:12-23` — `InMemoryRateLimiter` uses per-process dict | Under multiple uvicorn workers, each process has its own in-memory counter — rate limit is per-worker, not global | Always use Redis-backed limiter in production; document requirement |
| Medium | **Silent DB failure on startup** | `backend/app/main.py:53-57` — lifespan catches and logs but does not prevent app from starting | App can start with a broken database connection; first user request gets a connection error instead of a clear health-check failure | Make DB health check a startup hard dependency or improve `GET /health` to ping database |
| Medium | **Supabase PgBouncer connection drops** | `backend/tests/real_db/conftest.py:30` — `statement_cache_size=0`, transient `ConnectionDoesNotExistError` in test runs | Intermittent test failures under load; may cause request failures in production during traffic spikes | Implement connection retry logic; consider direct Postgres connection for non-pooled routes |
| Low | **No health endpoint DB check** | `backend/app/main.py:164` — health router registered but `GET /api/v1/health` only returns 200 | Health endpoint reports "ok" even when database is down — orchestrator won't detect DB failure | Add DB ping + Redis ping to health check |

### 2) Technical Debt

| Debt item | Why it exists | Where | Risk if ignored | Suggested fix |
|-----------|---------------|-------|-----------------|---------------|
| No linting/formatter | Not configured in project | No `.flake8`, `.pylintrc`, `.ruff.toml` in project root | Code style drifts; CI has no style checks | Add ruff configuration to `pyproject.toml`; add lint step to CI |
| No pre-commit hooks | Not configured | No `.pre-commit-config.yaml` | Commits can include secrets or unformatted code | Add pre-commit with ruff, secrets scanner |
| `_blacklisted_tokens` was in-memory set | JWT blacklist was module-level `set()` | `backend/app/services/auth.py:16` | ✅ Fixed — now Redis-backed with in-memory fallback | ✅ `_is_blacklisted` / `_add_to_blacklist` use `get_redis()` |
| Repository-free services | Services directly use SQLAlchemy sessions | `backend/app/services/*.py` | Harder to unit-test in isolation and swap storage backend | Consider introducing repository abstractions for complex queries |
| Sequential queries in dashboard | `backend/app/services/reports.py` executed 8 sequential `db.execute` calls | Slow dashboard load with large datasets | ✅ Fixed — now uses `asyncio.gather` | ✅ All queries execute concurrently |
| No connection pooling limits for async | `backend/app/core/database.py:17` uses `NullPool` when `ASYNC_NULLPOOL=1` | Dev/test only — production uses default pool | Low in production | Ensure production runs with pool_size=5 as configured |
| SAEnum missing `values_callable` (fixed) | Initial models used enum `.name` (uppercase) which didn't match DB lowercase values | `backend/app/models/user.py:26-27` plus event/registration/attendance/notification | Now fixed with `values_callable=lambda obj: [e.value for e in obj]` | ✅ Applied across all 5 model files |
| `events.coordinator_id` NOT NULL (fixed) | DB column was NOT NULL but model defined nullable=True | Supabase DB: `ALTER TABLE events ALTER COLUMN coordinator_id DROP NOT NULL` | Would cause IntegrityError on event creation without coordinator | ✅ Applied via Supabase migration |

### 3) Security Concerns

| Risk | OWASP category | Evidence | Current mitigation | Gap |
|------|----------------|----------|--------------------|-----|
| ~~JWT blacklist in memory~~ **FIXED** | N/A | `backend/app/services/auth.py` | ✅ Redis-backed with in-memory fallback | ✅ Cross-worker revocation via Redis |
| bcrypt rounds now configurable | N/A | `backend/app/core/security.py:53` — `bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS)` | Default rounds (12) | ✅ Configurable via `BCRYPT_ROUNDS` env var in config.py |
| Health endpoint unauthenticated + unrate-limited | N/A | `backend/app/main.py:139` — rate limiter skips health path | Health endpoint is unauthenticated and unrate-limited | Low risk for internal use but could be abused if exposed publicly |

### 4) Performance and Scaling Concerns

| Concern | Evidence | Current symptom | Scaling risk | Suggested improvement |
|---------|----------|-----------------|-------------|-----------------------|
| ~~Sequential queries in dashboard~~ **FIXED** | `backend/app/services/reports.py` — now `asyncio.gather` | ✅ Parallelized | ✅ Fixed | ✅ All 8 queries concurrent |
| ~~In-memory JWT blacklist~~ **FIXED** | `backend/app/services/auth.py` — now Redis-backed | ✅ Cross-worker revocation | ✅ Fixed | ✅ Redis `SETEX` + in-memory fallback |
| In-memory rate limiter | `backend/app/middleware/rate_limit.py:12-23` | Rate limit is per-process under multi-worker | Medium — bypassed by distributing requests across workers | Ensure Redis is configured in production |

### 5) Fragile/High-Churn Areas

| Area | Why fragile | Churn signal | Safe change strategy |
|------|-------------|-------------|----------------------|
| `backend/app/main.py` | Central wiring of lifespan, middleware, routers, rate limiters | 11 commits in last 90 days (highest churn) | Add tests for each middleware/router registration |
| `backend/tests/test_notifications.py` | Newest module — rapidly evolving | 7 commits | Test inline with each feature addition |
| `backend/app/api/deps.py` | Auth deps used by all protected routes — any breakage cascades | 4 commits | Maintain auth unit tests |
| `backend/tests/test_config.py` | Config validation tests sensitive to env changes | 4 commits | Keep tests updated alongside config changes |
| `backend/tests/test_rate_limit.py` | Rate limiter tests sensitive to timing | 4 commits | Use fakeredis for deterministic tests |

### 6) Resolved Decisions

1. **JWT blacklist** → **Migrated to Redis**. ✅ Done. Redis `SETEX` with TTL + in-memory fallback.
2. **Linter/formatter** → **None**. User confirmed no linter/formatter should be added.
3. **Health endpoint** → **Keep as-is**. User confirmed no DB/Redis ping needed.
4. **Pre-commit hooks** → **None**. User confirmed no pre-commit hooks.
5. **bcrypt rounds** → **Configurable via `BCRYPT_ROUNDS` env var**. ✅ Done. Default 12.
6. **Dashboard queries** → **Parallelized with `asyncio.gather`**. ✅ Done.

### 7) Evidence

- `backend/requirements.txt` (dependencies)
- `.github/workflows/ci.yml` (CI config)
- Scan output: git log (high-churn files)
- `backend/app/middleware/rate_limit.py:12` (in-memory limiter)
- `backend/app/services/auth.py:16` (in-memory blacklist — ✅ now Redis-backed)
- `backend/app/services/reports.py` (sequential queries — ✅ now `asyncio.gather`)
- `backend/app/models/user.py:26-27` (SAEnum values_callable fix)
- `backend/tests/real_db/conftest.py:30` (statement_cache_size=0, PgBouncer)
