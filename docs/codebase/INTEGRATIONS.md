# External Integrations

## Core Sections (Required)

### 1) Integration Inventory

| System | Type | Purpose | Auth model | Criticality | Evidence |
|--------|------|---------|------------|-------------|----------|
| PostgreSQL 16 (Supabase) | Database | Primary data store | Password (asyncpg) | High | `backend/requirements.txt:5`, `backend/app/core/config.py:27-31` |
| Redis 7 (local) | Cache/Queue | Rate-limiting sliding window (sorted sets) | Password/token | Medium | `backend/requirements.txt:10`, `backend/app/core/redis.py:4-5` |
| Upstash Redis | Cache | REST-based Redis alternative (no persistent TCP) | Token (URL + token) | Low | `backend/requirements.txt:12`, `backend/app/core/redis.py:7-10` |
| Supabase PgBouncer | Connection pooler | Managed PostgreSQL pooler (transaction mode) | Password | High | `backend/app/core/config.py:30`, `backend/tests/real_db/conftest.py:30` |

### 2) Data Stores

| Store | Role | Access layer | Key risk | Evidence |
|-------|------|--------------|----------|----------|
| PostgreSQL (Supabase) | Primary data store | SQLAlchemy 2.0 async + asyncpg | Connection pooler drops under load; `statement_cache_size=0` mitigates prepared-statement caching issues | `backend/app/core/database.py:14-18`, `backend/tests/real_db/conftest.py:30` |
| Redis (local/Upstash) | Rate-limiting state + token blacklist | redis-py async client / upstash-redis REST client | Not used for persistent state; downtime disables rate limiting (falls back to `InMemoryRateLimiter`) | `backend/app/core/redis.py` |

### 3) Secrets and Credentials Handling

- Credential sources: Environment variables via `.env` file (local) or host envs (CI/production). `DB_PASSWORD` is the primary secret — read from env var, URL-encoded, and used to construct `DATABASE_URL`.
- Hardcoding checks: No hardcoded secrets in source. `DB_USER`, `DB_HOST`, `DB_PORT`, `DB_NAME` are hardcoded defaults for the Supabase project `qwouxrnnwmkotkwraqme` in `config.py:28-32`.
- Rotation or lifecycle notes: No rotation mechanism documented.
- CI secrets: `JWT_SECRET` and `DATABASE_URL` set as env vars in `.github/workflows/ci.yml:64-65`.

### 4) Reliability and Failure Behavior

- Retry/backoff behavior: None configured on database. Redis connection has `retry_on_timeout=True` and `socket_connect_timeout=5`.
- Timeout policy: `REQUEST_TIMEOUT_SECONDS=30` in config (`app/core/config.py:46`); socket connect timeout 5s for Redis; no DB query timeout.
- Circuit-breaker or fallback behavior: Redis `get_redis()` returns `None` when not configured — rate limiter falls back to `InMemoryRateLimiter`. Supabase connection failure at startup is logged as warning but swallowed (app starts anyway).
- Pool: `NullPool` when `ASYNC_NULLPOOL=1` in CI/test, production uses default pooling (pool_size=5, max_overflow=3).

### 5) Observability for Integrations

- Logging around external calls: Lifespan logs Redis init status and DB connect check result via structlog. No structured logging around individual DB queries or query latency.
- Metrics/tracing coverage: None — no Prometheus, OpenTelemetry, or APM integration detected.
- Health endpoint: `GET /api/v1/health` returns 200 immediately without pinging DB or Redis — no readiness check.

### 6) Evidence

- `backend/app/core/config.py` (env vars for DB + Redis)
- `backend/app/core/database.py` (DB engine + session factory)
- `backend/app/core/redis.py` (Redis singleton + Upstash fallback)
- `backend/app/main.py` (lifespan integration initialization)
- `backend/tests/real_db/conftest.py` (real DB connection with `statement_cache_size=0`)
- `.github/workflows/ci.yml` (CI Postgres service)
