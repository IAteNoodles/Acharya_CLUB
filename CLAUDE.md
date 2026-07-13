# CLAUDE.md — Operating Manual for Acharya_CLUB

College Event Management System. FastAPI + SQLAlchemy 2.0 async + PostgreSQL (Supabase) + Redis.
All application code lives in `backend/`. Run every command below **from `backend/`**, not the repo root.

---

## Commands

```bash
# Tests (the default suite — mocked DB/Redis, no infra needed, ~seconds)
pytest -v                                    # excludes e2e via addopts = "-m 'not e2e'"
pytest --cov=app --cov-report=term-missing   # exact CI command

# Opt-in suites — DO NOT run these casually (see Failure Modes #7)
pytest tests/real_db/ -v                     # hits the LIVE Supabase DB in .env
pytest -m e2e -v                             # needs Docker (spins Postgres+Redis containers)

# Run the server
uvicorn app.main:create_app --factory --reload --port 8000
# API at /api/v1, interactive docs at /api/v1/docs

# Database
alembic upgrade head                         # apply migrations
python scripts/seed.py                       # DESTRUCTIVE: wipes tables, then seeds demo data

# Docker
docker compose up                            # dev, hot reload
docker compose --profile local-db up         # + local Postgres/Redis (offline dev)
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

CI (`.github/workflows/ci.yml`) runs only `pytest -v --cov=app --cov-report=term-missing`
against a throwaway Postgres, with `PYTHONPATH=.`. There is no lint, type-check, or deploy step — **by decision, not omission**.

---

## Architecture in one paragraph

Layered modular monolith: `api/v1/` routers (HTTP only) → `services/` (all business logic,
own their commits) → `models/` (SQLAlchemy 2.0 typed models) → Supabase Postgres. `schemas/`
holds Pydantic v2 request/response shapes. `core/` holds config (pydantic-settings), async
engine, JWT/bcrypt, Redis singleton, the `AppHTTPException` hierarchy, and structlog setup.
`middleware/` holds rate-limit / security-headers / timeout. Auth is a JWT payload **dict**
(`{"sub": ..., "role": ...}`) injected by `app/api/deps.py` — there is no ORM user object in
request context. No repository layer — services query the session directly (deliberate).

Layer rules (violating these is always wrong):
- Routers: no business logic, no queries. They parse input, call one service method, map to a response.
- Services: no HTTP imports for control flow — raise `app/core/exceptions.py` types instead.
- Models: no Pydantic. Schemas: no ORM logic.

Full architecture detail: `EXPLAIN.md` and `docs/codebase/*.md`.

## The module pattern (memorize this)

Every feature is built in this exact order, one conventional commit per step
(see git history of the notifications module for the canonical example):

1. `app/models/<x>.py` — model + enums, re-export in `models/__init__.py`, import in `alembic/env.py`
2. `alembic/versions/000N_<x>.py` — **hand-written** migration (never autogenerate)
3. `app/schemas/<x>.py` — Pydantic v2 schemas
4. `app/services/<x>.py` — `<X>Service` with `@staticmethod async def` methods, `db: AsyncSession` first param — **plus** `tests/test_<x>.py` service tests in the same commit
5. `app/api/v1/<x>.py` — router — plus API tests
6. Register router + OpenAPI tag in `app/main.py`
7. Notification triggers if the module changes state another user cares about
8. Update docs: `docs/api-specification.md`, `docs/codebase/*.md`, both READMEs

Commit format: `feat(<module>): <what>` / `fix:` / `docs:` / `test:`. Small, one concern per commit.

There is a `/add-module` skill that walks this end-to-end — use it for any new domain module.

---

## Failure modes — named rules

Each of these is a mistake that has either already happened in this repo or that the codebase
is specifically shaped to prevent. The rule is the fix; apply it without being asked.

**#1 The Helpful Tooling Rule — do not add linters, formatters, or pre-commit hooks.**
There is no ruff/black/flake8 config. That is a recorded decision
(`docs/codebase/CONCERNS.md` → Resolved Decisions), not a gap for you to fill. Same for
adding a DB ping to `/health` — declined. Never "improve" CI with lint steps.

**#2 The Enum Value Rule — every `SAEnum` column takes `values_callable=lambda obj: [e.value for e in obj]`.**
Enums are `(str, enum.Enum)` with lowercase snake_case **values** (`"in_college"`), and the DB
stores values, not member names. Omitting `values_callable` made SQLAlchemy write `IN_COLLEGE`
and broke against Supabase once already. Migrations must create the matching PG enum type and
**drop it in `downgrade()`** (`op.execute("DROP TYPE IF EXISTS <name>")`) — Postgres does not
drop enum types with the table.

**#3 The Exception Rule — new services raise `AppHTTPException` subclasses, never `fastapi.HTTPException`.**
Use `NotFoundException` (404), `UnauthorizedException` (401), `ForbiddenException` (403),
`ValidationException` (422, takes `errors` list), `ConflictException` (409) from
`app/core/exceptions.py`. `services/auth.py` and `services/user.py` raise `HTTPException`
directly — that is legacy, do not copy it into new code.

**#4 The Envelope Rule — new endpoints use `schemas/common.py`.**
`SuccessResponse[T]` = `{"success": true, "data": ...}`; `PaginatedResponse[T]` with nested
`meta: {page, limit, total, total_pages}`. Events and users have bespoke inline envelopes
(`items`/`users` + flat pagination) — that is the old style; follow registrations /
attendance / notifications / reports instead. Error bodies are always
`{"success": false, "error": {"code", "message"}}` — produced by the handlers, never built by hand in a router.

**#5 The Registration Rule — a router that isn't wired into `app/main.py` doesn't exist.**
After creating `app/api/v1/<x>.py`: import it in `create_app()`, `app.include_router(...)`,
and add its tag to `openapi_tags`. Router files own their own `prefix="/api/v1/<x>"` (only
health takes its prefix from `main.py`). Verify by hitting `/api/v1/openapi.json`.

**#6 The Mock Chain Rule — service tests must mirror the service's exact SQLAlchemy call chain.**
There is no test SQLite. Unit tests build `db = AsyncMock()` and stub the precise shape:
`db.execute.return_value = MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[...]))))`
for lists, `MagicMock(scalar_one_or_none=MagicMock(return_value=x))` for single rows,
`db.execute.side_effect = [r1, r2]` when the service runs multiple queries **in order**. Read
the service before writing the mock; a wrong chain fails confusingly or silently passes.

**#7 The Live Database Rule — `tests/real_db/` talks to the real Supabase instance.**
Never run it as part of routine verification; run it only when the change touches query
behavior and you intend to. It fails hard (no skip) without credentials. Also: its
`db_session` monkeypatches `commit` to a flush and rolls everything back — never assert
persistence across sessions there. `seed.py` **deletes all rows** first — never run it against
a DB you care about.

**#8 The Two-Manifest Rule — dependencies live in BOTH `pyproject.toml` and `requirements.txt`.**
CI and Docker install from `requirements.txt`; local metadata/pytest config lives in
`pyproject.toml`. A dependency added to only one of them breaks the other environment
(this exact bug is commit `36ce2e5`). Always update both.

**#9 The Unwired Settings Rule — verify a setting is actually consumed before relying on it.**
Known traps: `security.py` hardcodes `ALGORITHM = "HS256"` and ignores `JWT_ALGORITHM`;
`database.py` does **not** pass `DATABASE_POOL_SIZE`/`DATABASE_MAX_OVERFLOW` to the engine;
`.env.example` pool values (10/20) disagree with `config.py` defaults (5/3). Changing the env
var is not enough — check `core/` for the actual read.

**#10 The Commit Discipline Rule — never batch a feature into one commit.**
This repo's history is step-sized conventional commits (schema commit, service+tests commit,
router+tests commit, registration commit, docs commit). Match it. Services call
`await db.commit()` themselves — don't remove that on the theory that `get_db()` commits
(it does, but services owning their commit is the established pattern).

**#11 The Idiom Rule — no docstrings, no comment noise, absolute imports.**
The codebase has essentially zero docstrings; helper functions are `_`-prefixed and live at
the **bottom** of router files; imports are always absolute (`from app.core...`). Exception
imports inside service method bodies are an existing quirk — tolerated, not required. Write
code that is indistinguishable from the surrounding code.

**#12 The Async Test Rule — every async test needs `@pytest.mark.asyncio`** (or module-level
`pytestmark = pytest.mark.asyncio`). Loop scope is function-scoped; only E2E uses
session scope. Use real UUID strings for IDs in tests — schemas validate them.

---

## Quality bars (checkable, not adjectives)

A change is **done** when every applicable box passes:

**Any code change**
- [ ] `cd backend && pytest -v` → exit code 0, zero failures, zero errors (baseline: 333+ passing).
- [ ] `pytest --cov=app --cov-report=term-missing` → every file you added or touched shows no uncovered lines you can exercise; overall coverage does not drop below 97%.
- [ ] No new linter/formatter config files exist in the diff (`git diff --stat` shows no `.ruff.toml`, `.pre-commit-config.yaml`, etc.).
- [ ] Both `pyproject.toml` and `requirements.txt` updated if a dependency changed.

**New/changed endpoint**
- [ ] Appears in `/api/v1/openapi.json` with `BearerAuth` unless it is under the public prefixes (health/docs/openapi).
- [ ] Guarded by the correct dependency: `require_admin` / `require_teacher_or_admin` / `require_student` / `get_current_user` — and there is a test asserting 401 without a token AND a test asserting 403 for the wrong role.
- [ ] Success body is `{"success": true, ...}` via `common.py` generics; error paths return `{"success": false, "error": {"code", "message"}}` with the correct code string (`NOT_FOUND`, `FORBIDDEN`, `CONFLICT`, `VALIDATION_ERROR`, `UNAUTHORIZED`).
- [ ] Pagination (if any): `Query(1, ge=1)` page, `Query(20, ge=1, le=100)` limit, nested `meta`.
- [ ] `docs/api-specification.md` and the README endpoint tables mention it.

**New/changed model or migration**
- [ ] Model inherits `(TimestampMixin, Base)`; every enum column has `values_callable`.
- [ ] Model imported in `alembic/env.py` and re-exported in `models/__init__.py`.
- [ ] Migration: numeric revision (`"0003"`), correct `down_revision`, `upgrade()` AND `downgrade()`, downgrade drops any PG enum types it created.
- [ ] Unique constraints named `uq_*`, indexes named `*_idx`, matching model `__table_args__` exactly.
- [ ] `alembic upgrade head` then `alembic downgrade -1` then `upgrade head` all succeed against a scratch DB (docker `--profile local-db`), never against Supabase first.

**New service method**
- [ ] `@staticmethod async def`, `db: AsyncSession` first param, actor passed as the JWT payload dict.
- [ ] Every authorization branch (who may call it) and every conflict/404 branch has a dedicated test using `pytest.raises(<CustomException>, match=...)`.
- [ ] State changes another user should learn about create a notification via `NotificationService.create_notification` with the right `NotificationType`, and a test asserts `mock_create.assert_awaited_once()`.

**Tests**
- [ ] New module tests grouped in classes: `Test<X>Schemas`, `Test<X>Service`, `Test<X>API`.
- [ ] API tests: throwaway `FastAPI()` + only the router under test + `register_exception_handlers(app)` + `dependency_overrides[get_current_user]` + `httpx.AsyncClient(transport=ASGITransport(app=app))`.
- [ ] No test depends on Docker, Supabase, or network unless it lives in `tests/real_db/` or is marked `e2e`.

**Docs (this project maintains docs as first-class output)**
- [ ] If behavior changed: `docs/codebase/` files that state the old behavior are updated.
- [ ] If a known concern was fixed: mark it fixed in `docs/codebase/CONCERNS.md` the way existing entries do (strikethrough + ✅).

---

## Domain cheat-sheet

Roles: `student` (self-signup → ACTIVE), `teacher` (signup → PENDING, admin approves), `admin` (seeded only).
Event lifecycle: `in_college` created by **admin only**, starts DRAFT; `out_college` created by **student only**, starts PENDING; approve/reject by admin or the assigned coordinator (coordinator must be an active teacher). Only APPROVED events accept registrations.
Registration: student registers once per (event, role_type); needs event APPROVED + coordinator assigned + capacity (counted on ACCEPTED only); coordinator/admin accepts/rejects; PENDING is the only actionable state.
Attendance: bulk upsert (1–100 records) by coordinator/admin, only for students with ACCEPTED registration, unique per (event, student, date).
Notifications: 6 types, auto-created on teacher approve/reject, event approve/reject, registration accept/reject.

Known quirks (documented, don't "fix" silently — raise them if relevant):
`assign-coordinator` endpoint is gated only by `get_current_user` (no admin check);
`AttendanceStatus.LATE` exists but the bulk API only produces PRESENT/ABSENT;
rate-limit keys on `client.host` (all clients share one bucket behind a proxy);
lifespan swallows DB connection failure at startup (by design — health stays shallow).

## Environment

`.env` in `backend/` (see `.env.example`). Required: `DATABASE_URL` **or** `DB_PASSWORD`
(URL is constructed from Supabase defaults). `JWT_SECRET` auto-generates in development,
must be ≥32 chars in production. Redis optional — everything (rate limit, JWT blacklist)
degrades to in-memory. Tests need no env at all for the default suite; CI sets
`JWT_SECRET` + `DATABASE_URL` + `PYTHONPATH=.`.
