# External Integrations

## Core Sections (Required)

### 1) Integration Inventory

| System | Type (API/DB/Queue/etc) | Purpose | Auth model | Criticality | Evidence |
|--------|---------------------------|---------|------------|-------------|----------|
| PostgreSQL 16 | Database | Primary data store | Password (asyncpg) | High | `backend/requirements.txt:5`, `backend/app/core/config.py:27-31` |
| Redis 7 | Cache/Queue | Rate-limiting sliding window, optional Celery broker | Password/token | Medium | `backend/requirements.txt:10-11` |
| Upstash Redis | Cache | REST-based Redis alternative (no TCP) | Token | Low | `backend/requirements.txt:13`, `backend/app/core/redis.py:7-10` |
| Supabase | DB Host | Managed PostgreSQL hosting + connection pooling | Password | High | `backend/app/core/config.py:27-31`, `opencode.json:5-6` |

### 2) Data Stores

| Store | Role | Access layer | Key risk | Evidence |
|-------|------|--------------|----------|----------|
| PostgreSQL (Supabase) | Primary data store | SQLAlchemy 2.0 async + asyncpg | Connection pool exhaustion under load; SSL connection via pgBouncer | `backend/app/core/database.py:14-18` |
| Redis (local/Upstash) | Rate-limiting state | `redis-py` async client / Upstash REST client | Not used for persistent state, but downtime disables rate limiting (falls back to in-memory) | `backend/app/core/redis.py` |

### 3) Secrets and Credentials Handling

- Credential sources: Environment variables (`.env` file for local, GitHub Actions secrets for CI, host envs for production). `DB_PASSWORD` is intentionally excluded from `.env.example` — must be set via env var separately.
- Hardcoding checks: No hardcoded secrets found. Password is read from env var only.
- Rotation or lifecycle notes: Unknown — no rotation mechanism documented.

### 4) Reliability and Failure Behavior

- Retry/backoff behavior: None configured. Redis connection has `retry_on_timeout=True` and `socket_connect_timeout=5`.
- Timeout policy: `REQUEST_TIMEOUT_SECONDS=30` in config; Redis socket timeout 5s.
- Circuit-breaker or fallback behavior: Redis `get_redis()` returns `None` when not configured — rate limiter falls back to `InMemoryRateLimiter`. Database connect failure in lifespan is logged as warning but swallowed.

### 5) Observability for Integrations

- Logging around external calls: Lifespan logs Redis init status and DB connect check result via structlog. No structured logging around individual DB queries.
- Metrics/tracing coverage: None — no Prometheus, OpenTelemetry, or APM integration detected.
- Missing visibility gaps: No query latency tracking, no Redis health monitoring, no connection pool metrics.

### 6) Evidence

- `backend/app/core/config.py` (env vars for DB + Redis)
- `backend/app/core/database.py` (DB engine + session)
- `backend/app/core/redis.py` (Redis singleton + Upstash)
- `backend/app/main.py` (lifespan integration initialization)
