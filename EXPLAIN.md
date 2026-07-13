# EXPLAIN.md — A New Developer's Guide to Acharya_CLUB

This document explains what this repository does, how every folder and file fits together,
and — most importantly — **why** each architectural decision was made. Read it top to bottom
once; after that, `CLAUDE.md` is the day-to-day operating manual and `docs/codebase/` holds
the per-topic reference sheets.

---

## 1. What this repo does

Acharya_CLUB is a **production-grade REST API for managing the full lifecycle of college
events** at a single college:

1. A **student** or **admin** proposes an event (students propose out-of-college events,
   admins create in-college ones).
2. An **admin** (or the event's assigned **coordinator**, a teacher) approves or rejects it.
3. Students **register** for approved events as a *volunteer* or a *participant*.
4. The coordinator **accepts or rejects** registrations (capacity-limited).
5. During the event, the coordinator **bulk-marks attendance** per day.
6. Every state change that affects a user generates an **in-app notification**.
7. Teachers/admins see an aggregate **dashboard** (counts across all entities).

It is backend-only (a React SPA frontend is anticipated but not in this repo). There is one
deployable service: a FastAPI app served by Uvicorn, backed by Supabase PostgreSQL and
(optionally) Redis.

**Tech stack:** Python 3.12+/3.13 · FastAPI 0.138 · SQLAlchemy 2.0 (async, asyncpg) ·
Alembic · Pydantic v2 + pydantic-settings · PyJWT (HS256) + bcrypt · Redis / Upstash Redis ·
structlog · pytest (+asyncio, httpx, fakeredis, testcontainers) · Docker multi-stage ·
GitHub Actions.

---

## 2. Repository layout — every folder and file

```
Acharya_CLUB/
├── CLAUDE.md                     # Operating manual for AI/dev workflow
├── EXPLAIN.md                    # This document
├── README.md                     # Project-level README (badges, quickstart, API tables)
├── Acharya_club.pdf              # Original project brief/specification document
├── opencode.json                 # OpenCode editor config (Supabase MCP server)
├── .github/workflows/ci.yml     # CI: single test job with Postgres service container
│
├── docs/                         # First-class, actively maintained documentation
│   ├── architecture.md           # Long-form system design (737 lines)
│   ├── api-specification.md      # Full endpoint-by-endpoint API contract (2385 lines)
│   ├── database-schema.md        # Table-by-table schema reference (1322 lines)
│   ├── redis-plan.md             # Decision doc: how to run Redis in production (Upstash)
│   ├── codebase/                 # Auto-audited "state of the codebase" sheets
│   │   ├── ARCHITECTURE.md       #   layering, flow, patterns, known risks
│   │   ├── CONVENTIONS.md        #   naming, error/log/test conventions
│   │   ├── STRUCTURE.md          #   directory map, entry points, boundaries
│   │   ├── STACK.md              #   dependency inventory + key commands
│   │   ├── TESTING.md            #   test layers, fixtures, commands
│   │   ├── CONCERNS.md           #   prioritized risks + RESOLVED DECISIONS (read this!)
│   │   └── INTEGRATIONS.md       #   Supabase/Redis/Upstash integration details
│   └── superpowers/              # The development process artifacts
│       ├── specs/                #   design specs (what & why) per module
│       └── plans/                #   task-by-task implementation plans (how), with
│                                 #   exact code, verify commands, and commit points
│
└── backend/                      # THE application. All commands run from here.
    ├── pyproject.toml            # Project metadata, deps, pytest config (markers, addopts)
    ├── requirements.txt          # Pinned deps — the install source for CI and Docker
    ├── uv.lock                   # UV lockfile
    ├── .env.example              # Every env var with comments; copy to .env
    ├── alembic.ini               # Alembic config (URL comes from settings, not the ini)
    ├── Dockerfile                # 3-stage Alpine build: builder / development / production
    ├── docker-compose.yml        # Dev stack (+ optional local Postgres/Redis via profile)
    ├── docker-compose.prod.yml   # Production overrides (resources, restart, WARN logging)
    │
    ├── alembic/
    │   ├── env.py                # Async migration runner; imports all models for metadata
    │   └── versions/
    │       ├── 0001_initial_schema.py   # users, events, registrations, attendance + enums
    │       └── 0002_notifications.py    # notifications table + enum
    │
    ├── scripts/
    │   ├── entrypoint.sh         # Docker entrypoint: alembic upgrade head, then exec CMD
    │   └── seed.py               # Demo data seeder — WIPES ALL TABLES FIRST
    │
    ├── app/
    │   ├── main.py               # create_app() factory: lifespan, middleware, routers,
    │   │                         # custom OpenAPI, rate-limit + request-ID middleware
    │   ├── core/                 # Infrastructure (no business logic)
    │   │   ├── config.py         #   pydantic-settings Settings + validators
    │   │   ├── database.py       #   async engine, session factory, get_db() dependency
    │   │   ├── security.py       #   JWT create/verify, bcrypt hash/verify
    │   │   ├── redis.py          #   lazy singleton: Upstash REST > redis-py > None
    │   │   ├── exceptions.py     #   AppHTTPException hierarchy + response handlers
    │   │   └── logging_config.py #   structlog JSON logging setup
    │   ├── middleware/
    │   │   ├── rate_limit.py     #   sliding-window limiter (Redis sorted set / in-memory)
    │   │   ├── security.py       #   CSP, HSTS, X-Frame-Options, etc.
    │   │   └── timeout.py        #   asyncio.wait_for per request → 503 on timeout
    │   ├── models/               # SQLAlchemy 2.0 typed models + enums
    │   │   ├── base.py           #   Base + TimestampMixin (UUID id, created/updated_at)
    │   │   ├── user.py           #   User, Role, UserStatus
    │   │   ├── event.py          #   Event, EventType, EventCategory, EventStatus
    │   │   ├── registration.py   #   Registration, RegistrationRole, RegistrationStatus
    │   │   ├── attendance.py     #   Attendance, AttendanceStatus
    │   │   └── notification.py   #   Notification, NotificationType (6 values)
    │   ├── schemas/              # Pydantic v2 request/response models
    │   │   ├── common.py         #   SuccessResponse[T], PaginatedResponse[T], errors
    │   │   ├── auth.py / users.py / event.py / registration.py
    │   │   ├── attendance.py / notification.py / reports.py
    │   ├── services/             # ALL business logic; services own their commits
    │   │   ├── auth.py           #   module functions: signup/login/refresh/logout/get_me
    │   │   │                     #   + Redis JWT blacklist (bl:<token>)
    │   │   ├── user.py           #   module functions: teacher approval workflow
    │   │   ├── event.py          #   EventService (staticmethods)
    │   │   ├── registration.py   #   RegistrationService
    │   │   ├── attendance.py     #   AttendanceService
    │   │   ├── notification.py   #   NotificationService + message templates
    │   │   └── reports.py        #   ReportService (dashboard, asyncio.gather)
    │   └── api/
    │       ├── deps.py           # get_current_user + require_admin/teacher_or_admin/student
    │       └── v1/               # One router per module, prefix "/api/v1/<x>"
    │           ├── health.py, auth.py, users.py, events.py,
    │           ├── registrations.py, attendance.py, notifications.py, reports.py
    │
    └── tests/                    # 29 files, ~97% coverage, three distinct layers
        ├── conftest.py           # just an `app` fixture (create_app())
        ├── test_*.py             # unit/mock tests (AsyncMock DB, dependency_overrides)
        ├── test_e2e_workflows.py # full-stack E2E via testcontainers (marked `e2e`)
        └── real_db/              # integration tests against the REAL Supabase DB
            ├── conftest.py       # session engine + transaction-per-test rollback + user fixtures
            └── test_*.py
```

---

## 3. The request lifecycle

```
Client ──▶ Uvicorn ──▶ add_request_id ──▶ rate_limit ──▶ RequestTimeout(30s)
        ──▶ SecurityHeaders ──▶ CORS ──▶ Router (api/v1) ──▶ auth dependency (deps.py)
        ──▶ Service (business logic) ──▶ AsyncSession ──▶ Supabase Postgres
```

Details worth knowing:

- **Middleware order is reversed from registration order.** Starlette runs the *last-added*
  middleware first. In `main.py`, class middlewares are added (CORS → SecurityHeaders →
  Timeout), then two `@app.middleware("http")` functions (rate-limit, request-ID) — so at
  runtime the request-ID binder runs outermost, then rate limiting, then timeout, then
  headers, then CORS. If you add middleware, think about where it needs to sit at *runtime*.
- **Request ID**: a UUIDv4 is generated per request, bound into structlog contextvars (so
  every log line carries it), and returned as the `X-Request-ID` response header.
- **Rate limiting**: sliding window per `rl:{client_ip}:{path}` key. General endpoints get
  100 req/min; anything under `/api/v1/auth` gets 20 req/min; `/api/v1/health` is exempt.
  Redis available → sorted-set algorithm (ZREMRANGEBYSCORE + ZCARD + ZADD + EXPIRE);
  Redis absent → per-process in-memory list (fine for dev, not multi-worker safe).
  Blocked requests get 429 with a `Retry-After` header and the standard error envelope.
- **Timeout**: each request runs under `asyncio.wait_for` (default 30 s,
  `REQUEST_TIMEOUT_SECONDS`); timeouts return 503 `REQUEST_TIMEOUT`.
- **Response envelope**: every response, success or failure, is JSON with a `success`
  boolean. Errors are always `{"success": false, "error": {"code": "...", "message": "..."}}`
  — produced centrally by exception handlers, the rate limiter, and the timeout middleware,
  so clients can rely on one shape.

---

## 4. Authentication and authorization

**Scheme:** stateless JWT (HS256, PyJWT) with an access/refresh pair and rotation.

- **Access token**: 15 min TTL, payload `{"sub": user_id, "role": role, "type": "access", iat, exp}`.
- **Refresh token**: 7 days, payload `{"sub", "type": "refresh", iat, exp}` — *no role claim*;
  role is re-read from the DB at refresh time so a role change takes effect on next refresh.
- **Rotation**: `POST /auth/refresh` issues a new pair and **blacklists the old refresh
  token**. `POST /auth/logout` blacklists the refresh token.
- **Blacklist**: Redis key `bl:<token>` set via `SETEX` with a 7-day TTL (the refresh
  window). If Redis is down/unconfigured, a module-level in-memory set is the fallback —
  correct on a single process, lost on restart. This was migrated from in-memory-only to
  Redis deliberately (see `docs/codebase/CONCERNS.md`).
- **Password hashing**: bcrypt, rounds configurable via `BCRYPT_ROUNDS` (default 12).

**Authorization is role-claim-based, not DB-based.** `app/api/deps.py` decodes the token and
returns the raw payload dict; `require_admin`, `require_teacher_or_admin`, `require_student`
just inspect `payload["role"]`. Consequences you must internalize:

- Handlers and services receive a **dict** (`current_user["sub"]`, `current_user["role"]`),
  never a `User` ORM object. No DB hit per request for auth.
- A revoked/demoted user keeps their old role until the access token expires (≤15 min) —
  accepted trade-off for statelessness.
- Fine-grained checks (e.g. "is this user the event's coordinator?") happen **inside
  services** by comparing `current_user["sub"]` to rows.

**Signup rules**: email must end with `@college.edu`; students become ACTIVE immediately;
teachers are created PENDING and must be approved by an admin (`/users/{id}/approve`);
admins exist only via seeding.

**OpenAPI**: `main.py` installs a custom OpenAPI generator that marks every path as requiring
`BearerAuth` except `/api/v1/health`, `/docs`, `/redoc`, `/openapi.json` — so Swagger UI's
"Authorize" button works out of the box.

---

## 5. The domain model

Five tables. All inherit `TimestampMixin`: UUID primary key (Python-side `uuid4` default,
`gen_random_uuid()` server default in migrations), timezone-aware `created_at`/`updated_at`.

```
users ──1:N── events (created_by)          users ──1:N── registrations (student_id)
users ──1:N── events (coordinator_id)      users ──1:N── attendance (student_id)
users ──1:N── notifications (user_id)      users ──1:N── attendance (marked_by)
events ──1:N── registrations               events ──1:N── attendance
```

| Table | Key columns | Enums | Constraints/Indexes |
|---|---|---|---|
| `users` | name, email (unique), password_hash, role, status | Role: student/teacher/admin · UserStatus: pending/active/rejected | `users_role_status_idx` |
| `events` | title, description, event_type, category, status, venue, start/end_date, max_registrations, created_by, coordinator_id (nullable) | EventType: in_college/out_college · EventCategory: volunteer/participant/both · EventStatus: draft/pending/approved/rejected | `events_status_type_idx`, `events_coordinator_id_idx`, `events_created_by_idx`, `events_start_date_idx` |
| `registrations` | event_id, student_id, role_type, status, registered_at | RegistrationRole: volunteer/participant · RegistrationStatus: pending/accepted/rejected | **unique** `uq_reg_event_student_role` (event, student, role_type); `reg_student_id_idx`, `reg_event_status_idx` |
| `attendance` | event_id, student_id, marked_by, attendance_date, status, marked_at | AttendanceStatus: present/absent/late | **unique** `uq_att_event_student_date` (event, student, date); `att_event_date_idx`, `att_student_id_idx` |
| `notifications` | user_id, type, title, message, related_entity_type/id, is_read | NotificationType: registration_accepted/rejected, event_approved/rejected, teacher_approved/rejected | index on user_id |

**Business rules, per module (the source of truth is the service layer):**

- **Events** (`services/event.py`): visibility is role-scoped — students see only APPROVED,
  teachers see events they coordinate or created, admins see all. Only admins create
  `in_college` events (start as DRAFT); only students create `out_college` (start as
  PENDING). Dates validated (no past start, end ≥ start). Approve/reject allowed for admin
  or the assigned coordinator (who must have role teacher); can't approve a REJECTED event
  or re-approve. Approval/rejection notifies the creator.
- **Registrations** (`services/registration.py`): only for APPROVED events **with a
  coordinator assigned**; capacity = `max_registrations` counted against ACCEPTED rows only
  (0 = unlimited); a student registers at most once per (event, role_type) — so once as
  volunteer *and* once as participant is legal. Accept/reject only from PENDING, only by
  admin or the coordinator; both notify the student.
- **Attendance** (`services/attendance.py`): bulk upsert of 1–100 records per call, only by
  admin/coordinator, only for students holding an ACCEPTED registration; unique per
  (event, student, date) with update-if-exists semantics.
- **Notifications** (`services/notification.py`): template map renders title/message per
  type; users can only read/mark their own; `mark_all_as_read` is a single bulk UPDATE.
- **Reports** (`services/reports.py`): one dashboard endpoint; 8 aggregate queries executed
  concurrently with `asyncio.gather` (was sequential; parallelized deliberately).

---

## 6. Architectural decisions and their rationale

Each of these was a conscious choice. When you're tempted to change one, find the reasoning
first (usually in `docs/codebase/CONCERNS.md` "Resolved Decisions" or a `docs/superpowers/` spec).

1. **Layered modular monolith, no microservices.** Single college, single deployment.
   Layers (`api → services → models`) give the seams; extraction can come later if ever
   needed. Cross-layer imports are the thing to police in review.

2. **Async-first everywhere.** FastAPI + asyncpg + SQLAlchemy 2.0 `AsyncSession` +
   redis-py asyncio. Rationale: the workload is I/O-bound (DB + Redis), and consistency
   matters more than raw need — there is no sync code path to accidentally block the loop.

3. **No repository pattern — services query the session directly.** Recorded as a known
   trade-off: fewer layers and faster iteration, at the cost of unit tests needing to mock
   SQLAlchemy's call chains precisely. Don't introduce repositories piecemeal; that's a
   project-wide decision.

4. **Services are stateless `@staticmethod` classes** (auth/user predate this and are module
   functions). `db: AsyncSession` is always the first parameter, injected by the router from
   `get_db()`. There is no DI container. Services **commit their own transactions** and
   trigger notifications inline — a service method is the complete unit of business work.

5. **Custom exception hierarchy instead of `HTTPException`.**
   `AppHTTPException` subclasses carry `error_code` + `status_code`; registered handlers
   render the uniform envelope. This keeps services HTTP-framework-agnostic-ish and clients
   able to switch on stable `code` strings. (auth/user services still raise `HTTPException` —
   legacy; new code must not.)

6. **Uniform `{success, ...}` envelope.** Chosen so a frontend can uniformly check
   `res.success`. `schemas/common.py` provides `SuccessResponse[T]` and
   `PaginatedResponse[T]` (nested `meta`). Historical note: events/users predate `common.py`
   and inline their own envelopes with flat pagination — a known inconsistency; new modules
   follow `common.py`.

7. **App factory (`create_app()`) + lifespan.** Enables per-test app construction, E2E
   re-instantiation with different env, and `uvicorn app.main:create_app --factory`.
   Lifespan initializes Redis, builds the two rate limiters onto `app.state`, and does a
   *best-effort* DB connectivity check that only warns on failure — deliberately non-fatal
   so the app can boot before/without the DB (and health stays a shallow liveness probe;
   adding a DB ping was explicitly declined).

8. **Supabase Postgres behind PgBouncer.** This drives two non-obvious settings:
   `statement_cache_size=0` on asyncpg connections (PgBouncer transaction pooling breaks
   prepared-statement caching) and the `ASYNC_NULLPOOL=1` env toggle that swaps in
   `NullPool` for tests/CI. DB credentials default to the Supabase pooler host; you supply
   `DB_PASSWORD` (URL constructed, password URL-encoded) or a full `DATABASE_URL`.

9. **Enums store lowercase string values.** Every enum is `(str, enum.Enum)` with lowercase
   values, and every `SAEnum` column passes `values_callable=lambda obj: [e.value for e in obj]`.
   This exists because the initial models wrote Python member *names* (`STUDENT`) while the
   Supabase enum types held *values* (`student`) — a real production bug, fixed across all
   five models. Treat `values_callable` as mandatory.

10. **Hand-written Alembic migrations, numeric revisions.** Revisions are `"0001"`, `"0002"`
    in a linear chain; `alembic/env.py` builds the async engine from `settings.DATABASE_URL`
    (the ini has no URL) and imports every model module explicitly. Downgrades must
    `DROP TYPE IF EXISTS` each PG enum because Postgres doesn't drop enum types with tables.

11. **Redis is optional by design — everything degrades.** `get_redis()` prefers Upstash
    REST (works on serverless, no TCP), else `redis-py` on `REDIS_URL`, else returns `None`.
    Rate limiter falls back to in-memory; JWT blacklist falls back to an in-memory set. The
    degradations are single-process-correct only — production must run Redis (Upstash is the
    chosen provider, see `docs/redis-plan.md`).

12. **Structured JSON logging with request correlation.** structlog + `JSONRenderer`; the
    request-ID middleware binds `request_id` into contextvars so every log line in a request
    is correlatable. No metrics/tracing yet (known gap).

13. **Security posture:** strict security headers on every response (CSP, HSTS,
    X-Frame-Options DENY, etc.), CORS restricted to configured origins, auth-route rate
    limiting 5× stricter than general, request timeout, JWT secret validated ≥32 chars
    (auto-generated with a warning in development only).

14. **No linter, no formatter, no pre-commit hooks — on purpose.** Recorded decision.
    CI is test-only. Don't add them.

15. **Two dependency manifests.** `requirements.txt` is what CI and Docker install;
    `pyproject.toml` carries metadata + pytest config + dev dependency group. Both must be
    updated together (a missed sync already caused a broken CI once — commit `36ce2e5`).

16. **Docker: one Dockerfile, three stages.** `builder` compiles wheels on Alpine;
    `development` adds hot-reload + healthcheck; `production` is a stripped non-root image
    whose entrypoint runs `alembic upgrade head` (tolerantly — warns and continues on
    failure) before exec'ing uvicorn. Compose has an optional `local-db` profile that adds
    Postgres 16 + Redis 7 for fully offline development.

---

## 7. The development process (how code gets built here)

This repo is built with a **spec → plan → execute** loop, visible in `docs/superpowers/`:

1. **Design spec** (`docs/superpowers/specs/…-design.md`): endpoint shapes, schemas, service
   methods, file map. Short (~100–200 lines), decides *what and why*.
2. **Implementation plan** (`docs/superpowers/plans/…`): the spec exploded into numbered
   tasks, each with the exact code to write, a **verify command** (often a one-line
   `python -c "import …; print('OK')"` or a pytest invocation), and a **commit point** with
   the exact conventional-commit message.
3. **Execution**: tasks are implemented in order, one commit each. Look at the notifications
   module in `git log` — model → migration → schemas → service+tests → router+tests →
   registration in main.py → per-workflow integration commits → docs commit.

Conventions that follow from this:
- Conventional commits: `feat(scope):`, `fix(scope):`, `test:`, `docs:`; small and atomic.
- Tests land **in the same commit** as the code they cover, at three layers
  (schemas / service / API) grouped into `Test<X>Schemas` / `Test<X>Service` / `Test<X>API`
  classes in one `tests/test_<x>.py`.
- Documentation is a deliverable, not an afterthought: `docs/api-specification.md`,
  `docs/database-schema.md`, `docs/codebase/*` and both READMEs get updated when behavior
  changes, and fixed concerns are struck through in `CONCERNS.md`.

---

## 8. Testing strategy (three layers, know which you're in)

| Layer | Where | DB | How | When to run |
|---|---|---|---|---|
| **Unit / mock** | `tests/test_*.py` | `AsyncMock` — no real DB at all | Services get a mocked session; API tests build a throwaway `FastAPI()` with just the router + `dependency_overrides` for auth + patched service; driven by `httpx.AsyncClient(ASGITransport)` | Always — this is `pytest -v` and what CI runs |
| **Real DB** | `tests/real_db/` | **Live Supabase** from `.env` | Session-scoped engine (`NullPool`, `statement_cache_size=0`); each test runs inside a transaction whose `commit` is monkeypatched to `flush`, rolled back at teardown; `admin_user`/`teacher_user`/`student_user` fixtures | Only deliberately, when query behavior changed |
| **E2E** | `tests/test_e2e_workflows.py` (marker `e2e`) | Fresh Docker containers (Postgres+Redis via testcontainers) | Purges `app.*` from `sys.modules`, points env at containers, recreates schema, runs whole user journeys through real HTTP calls | Before releases / big changes; needs Docker |

Key facts:
- Default run **excludes** e2e (`addopts = "-m 'not e2e'"`). Real-DB tests are excluded only
  by path habit (`testpaths=["tests"]` *does* include them) — they fail hard, not skip, when
  the DB is unreachable. Run `pytest tests/ --ignore=tests/real_db -v` if you need to be safe
  without credentials.
- There is **no SQLite substitute**. Unit tests must stub the exact SQLAlchemy result chain
  the service uses (`.scalars().all()`, `.scalar_one_or_none()`, `db.scalar`, `db.get`,
  ordered `execute.side_effect`). This is the price of decision #3 (no repositories).
- Coverage is ~97% with 333+ tests; CI enforces no threshold, but the working bar is
  "don't make it drop."
- Historical flake worth knowing: `test_config.py` reloads `app.core.*` modules; it now
  save/restores `sys.modules` entries so exception **class identity** stays stable for other
  tests (`pytest.raises` breaks if a module is re-imported mid-suite). Be very careful with
  any test that touches `sys.modules` or reloads config.

Seed data (`python scripts/seed.py` — **wipes all tables first**): 1 admin
(`admin@college.edu` / `Admin@123`), 3 teachers (`Teacher@123`; one ACTIVE, one PENDING, one
REJECTED), 4 students (`Student@123`; three ACTIVE, one PENDING), 4 events in assorted
states (including one past event with attendance), 7 registrations, 2 attendance rows.

---

## 9. Configuration reference

All config is env vars / `.env` via pydantic-settings (`app/core/config.py`), case-sensitive.

| Variable | Default | Notes |
|---|---|---|
| `DATABASE_URL` | constructed | If empty, built from `DB_USER`/`DB_PASSWORD`/`DB_HOST`/`DB_PORT`/`DB_NAME` (Supabase pooler defaults) with `?ssl=require`; **error if neither URL nor password set** |
| `JWT_SECRET` | auto-gen (dev only) | Must be ≥32 chars; placeholder value rejected; production must set it |
| `JWT_ACCESS_EXPIRE_MINUTES` / `JWT_REFRESH_EXPIRE_DAYS` | 15 / 7 | |
| `BCRYPT_ROUNDS` | 12 | |
| `REDIS_URL` | `redis://localhost:6379/0` | `UPSTASH_REDIS_REST_URL` + `_TOKEN` take precedence (read directly from env, not Settings) |
| `CORS_ORIGINS` | localhost:5173, localhost:8000 | JSON array |
| `REQUEST_TIMEOUT_SECONDS` | 30 | |
| `API_PREFIX` | `/api/v1` | |
| `ASYNC_NULLPOOL` | unset | `1` → engine uses NullPool (tests/CI) |

**Traps** (verified in code, easy to get wrong):
- `JWT_ALGORITHM` exists in Settings but `security.py` hardcodes `HS256`.
- `DATABASE_POOL_SIZE` / `DATABASE_MAX_OVERFLOW` exist in Settings but are **not passed** to
  `create_async_engine` — the engine uses SQLAlchemy defaults (or NullPool).
- `.env.example` pool numbers (10/20) disagree with `config.py` defaults (5/3); neither is wired.

---

## 10. Known gaps and quirks (documented, intentional-until-decided)

These are catalogued in `docs/codebase/CONCERNS.md`; the ones that trip people up:

- **`PATCH /events/{id}/assign-coordinator` has no admin guard** — only `get_current_user`.
  Any authenticated user can currently assign coordinators. Likely an oversight; raise it
  before building on it.
- **`AttendanceStatus.LATE` is unreachable** — the bulk API maps `present: bool` to
  PRESENT/ABSENT only.
- **Rate limiting keys on `request.client.host`** — behind a proxy/LB without forwarded-IP
  handling, all clients share one bucket.
- **In-memory fallbacks (rate limit, blacklist) are per-process** — multi-worker production
  requires Redis; this is a documented deployment requirement, not a bug.
- **Startup DB check is non-fatal and `/health` never pings the DB** — explicit decision;
  orchestrators get liveness, not readiness.
- **JWT blacklist keys embed the whole token** (`bl:<jwt>`) with a flat 7-day TTL.
- **Two response-envelope styles coexist** (events/users vs. everything else) — converge on
  `schemas/common.py` for new work.
- **PgBouncer can drop connections under load** (`ConnectionDoesNotExistError` seen in test
  runs) — no retry logic exists yet.

---

## 11. Where to look when…

| You need to… | Look at |
|---|---|
| Add a whole new domain module | `/add-module` skill; notifications module commits as the exemplar |
| Change the DB schema | `/db-migration` skill; `alembic/versions/0002_notifications.py` as template |
| Verify a change end-to-end | `/verify` skill |
| Understand an endpoint's contract | `docs/api-specification.md` |
| Understand a table | `docs/database-schema.md` |
| Know why something wasn't "fixed" | `docs/codebase/CONCERNS.md` → Resolved Decisions |
| See the intended design of a module | `docs/superpowers/specs/` |
| Copy the canonical endpoint/service/test shape | registrations or notifications module (newest conventions) |
