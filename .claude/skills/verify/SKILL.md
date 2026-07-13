---
name: verify
description: Verify a change to the Acharya_CLUB backend end-to-end — run the right test layers (and ONLY the safe ones by default), boot the app, and exercise the changed endpoints over real HTTP with minted JWTs. Use before committing any nontrivial change, or when asked "does this work?".
---

# Verify a Backend Change

Run from `backend/`. Escalate through the levels below — stop at the first failure, report
it with the actual output, and don't mark anything verified that you didn't observe.

## Level 0 — Know what you're verifying

`git diff --stat` (or the working-tree change). Decide which layers the change touches:
schema/model → include Level 3; service/router → Levels 1+2; infra (middleware, config,
core) → Levels 1+2 plus the specific middleware behavior at Level 2.

## Level 1 — The default suite (always)

```bash
pytest -v                                       # mocked DB/Redis; excludes e2e via addopts
pytest --cov=app --cov-report=term-missing      # exact CI command
```

Pass criteria: exit 0, **zero** failures/errors (baseline 333+ passing), coverage did not
drop below ~97%, and every file you touched shows no newly-uncovered lines.

⚠️ Safety rules:
- **Do NOT run `pytest tests/real_db/`** unless the change is query behavior AND you intend
  to hit the live Supabase DB — it does not skip, it connects.
- **Do NOT run `python scripts/seed.py`** against Supabase — it deletes every row first.
- `pytest -m e2e -v` needs Docker; run it for release-level verification or when the change
  touches lifespan/middleware wiring, migrations, or cross-module workflows.

## Level 2 — Boot and exercise over HTTP (any behavior change)

The unit suite mocks the DB, so it cannot catch wiring mistakes (unregistered router, wrong
prefix, broken enum serialization, middleware order). Boot the real app.

**Option A — no infra needed (offline smoke):** app boots even without a reachable DB
(startup DB check only warns), so router registration / OpenAPI / auth guards / middleware
can be verified with no database:

```bash
JWT_SECRET='local-verify-secret-at-least-32-characters!!' \
DATABASE_URL='postgresql+asyncpg://postgres:x@localhost:5/x' \
uvicorn app.main:create_app --factory --port 8000 &
sleep 2
```

**Option B — full stack (data paths):** `docker compose --profile local-db up -d`, point
`DATABASE_URL` at `postgresql+asyncpg://postgres:localdev@localhost:5432/acharya`, run
`alembic upgrade head`, optionally `python scripts/seed.py` (safe here — scratch DB), then
start uvicorn. Seed credentials: `admin@college.edu`/`Admin@123`,
`rajesh.kumar@college.edu`/`Teacher@123`, `priya.singh@college.edu`/`Student@123`.

**Checks (adapt to the change):**

```bash
# Health + envelope shape
curl -s localhost:8000/api/v1/health | python -m json.tool

# Endpoint exists in OpenAPI with BearerAuth
curl -s localhost:8000/api/v1/openapi.json | python -c "
import json,sys; spec=json.load(sys.stdin)
p='/api/v1/<changed-path>'; assert p in spec['paths'], f'{p} not registered'
print('registered OK')"

# 401 without token — body must be the standard envelope
curl -s -o /dev/null -w '%{http_code}\n' localhost:8000/api/v1/<changed-path>

# Mint tokens per role (works without DB for guard checks; use login for data paths)
TOKEN=$(python -c "
from app.core.security import create_access_token
print(create_access_token(user_id='00000000-0000-0000-0000-000000000001', role='student'))")

# 403 for the wrong role, 200/201 + {"success": true, ...} for the right one
curl -s -H "Authorization: Bearer $TOKEN" localhost:8000/api/v1/<changed-path> | python -m json.tool
```

For data-path changes (Option B): drive the actual user flow — e.g. login as student →
register for the seeded approved event → login as teacher → accept → verify the student got
a notification (`GET /api/v1/notifications`). The E2E file
(`tests/test_e2e_workflows.py`) shows the canonical journeys to imitate.

Kill the server and `docker compose --profile local-db down` when done.

## Level 3 — Schema changes only

Follow the `/db-migration` skill's verification procedure (scratch-DB round trip:
`upgrade head` → `downgrade -1` → `upgrade head`, enum-type check, model/DB agreement).

## Level 4 — Report

State plainly, with evidence:
- Test counts before/after, coverage number, exact commands run.
- Which endpoints you exercised over HTTP and the observed status codes/bodies.
- Anything you did NOT verify and why (e.g. "did not run real_db suite — no query changes").

A change is verified only if Level 1 passed AND (for behavior changes) you observed the new
behavior over HTTP at Level 2. "Tests pass" alone is not verification for wiring changes.

## Known sharp edges

- Middleware order is reverse of registration order in `main.py` — verify header/limit
  behavior with curl, not by reading the registration sequence.
- Rate limiting: rapid curls to `/api/v1/auth/*` hit the 20/min limiter (429 + Retry-After)
  — that's correct behavior, not a bug; health is exempt.
- `test_config.py` manipulates `sys.modules` — if you see bizarre exception-identity
  failures after config changes, re-run the suite in isolation before digging.
- E2E purges `app.*` modules and swaps env vars; never mix `-m e2e` with other suites in
  one pytest invocation.
