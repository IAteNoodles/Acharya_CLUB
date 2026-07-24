# MISTAKES.md — Code Review Findings and Their Impact

A catalog of every mistake found in this codebase, with its concrete impact. Compiled from a
full audit of the source, tests, migrations, git history, and `docs/codebase/CONCERNS.md`.

How to read this file:
- **Status**: 🔴 open · ✅ fixed (mistake was made, later corrected — kept here because the
  user asked for *all* mistakes) · 📋 decision (looks like a mistake but is a recorded,
  deliberate choice — do not "fix").
- **Severity**: judged by production impact, not code aesthetics.
- Every entry has a file reference so it can be verified in one jump.

---

## Summary table

| # | Severity | Status | Mistake |
|---|----------|--------|---------|
| 1 | High | 🔴 | `assign-coordinator` endpoint has no admin/role guard |
| 2 | High | 🔴 | `seed.py` imports `passlib` — not in any dependency manifest; seeding crashes |
| 3 | High | ✅ | SAEnum columns written member NAMES instead of values (broke against Supabase) |
| 4 | High | ✅ | JWT blacklist was an in-memory `set()` — lost on restart, per-worker |
| 5 | Medium | 🔴 | Logout does not revoke access tokens (only refresh) |
| 6 | Medium | 🔴 | Registration capacity/duplicate checks are race-prone (TOCTOU → oversell or 500) |
| 7 | Medium | 🔴 | Attendance bulk-mark runs 1 SELECT per record (N+1, up to 100 round trips) |
| 8 | Medium | 🔴 | `JWT_ALGORITHM`, `DATABASE_POOL_SIZE`, `DATABASE_MAX_OVERFLOW` settings exist but are never used |
| 9 | Medium | 🔴 | Rate limiter keys on `client.host` — one shared bucket behind any proxy |
| 10 | Medium | 🔴 | In-memory fallbacks (blacklist set, rate-limit dict) grow without bound |
| 11 | Medium | 🔴 | Two incompatible response-envelope styles (events/users vs. everything else) |
| 12 | Medium | ✅ | Dependencies added to `requirements.txt` only — `pyproject.toml` forgotten (broke pytest) |
| 13 | Medium | ✅ | Dashboard ran 8 queries sequentially |
| 14 | Medium | ✅ | `events.coordinator_id` NOT NULL in DB while model said nullable (schema drift) |
| 15 | Medium | ✅ | `test_config.py` reloaded `app.core.*` modules, breaking exception identity (flaky suite) |
| 16 | Low | 🔴 | `reject_teacher` can reject an already-ACTIVE teacher |
| 17 | Low | 🔴 | `AttendanceStatus.LATE` exists but is unreachable through the API |
| 18 | Low | 🔴 | Event date validation mixes server-local `date.today()` with tz-aware input |
| 19 | Low | 🔴 | `services/auth.py` / `services/user.py` raise raw `HTTPException` instead of the custom hierarchy |
| 20 | Low | 🔴 | Hand-rolled email validation instead of `EmailStr` |
| 21 | Low | 🔴 | Blacklist keys embed the entire JWT; TTL always 7 days regardless of remaining life |
| 22 | Low | 🔴 | bcrypt silently truncates passwords at 72 bytes while schema allows 100 chars |
| 23 | Low | 🔴 | `.env.example` pool values (10/20) contradict `config.py` defaults (5/3) — neither wired |
| 24 | Low | 🔴 | `tests/real_db/` is inside `testpaths` and fails hard (no skip) without live credentials |
| 25 | Low | 🔴 | Redundant double-commit: `get_db()` commits and every service commits |
| 26 | Low | 🔴 | Deprecated `X-XSS-Protection` header still set |
| 27 | Info | 📋 | No linter/formatter/pre-commit; shallow `/health`; startup swallows DB failure — recorded decisions, not mistakes |

---

## High severity — open

### 1. `assign-coordinator` has no authorization guard
**Where:** `backend/app/api/v1/events.py` (`PATCH /events/{id}/assign-coordinator`, gated only by `get_current_user`); `EventService.assign_coordinator` (`app/services/event.py:~265`) performs no role check either.
**Mistake:** Every other privileged action uses `require_admin` / `require_teacher_or_admin`, or checks `user["role"]` in the service. This endpoint — which controls *who can approve events and manage registrations* — accepts any valid token. A student can assign any active teacher as coordinator of any event.
**Impact:** Privilege-escalation path: a student who created an `out_college` event can assign a coordinator themselves, satisfying the "coordinator assigned" precondition for registrations, and can redirect approval authority for any event. Breaks the intended admin-controlled workflow entirely.
**Fix:** Add `Depends(deps.require_admin)` to the route; add a 403 test for student and teacher roles.

### 2. `seed.py` depends on `passlib`, which is not installed anywhere
**Where:** `backend/scripts/seed.py:3` (`from passlib.context import CryptContext`); `passlib` appears in neither `requirements.txt` nor `pyproject.toml`.
**Mistake:** The seeder uses a different hashing stack than the application (`app/core/security.py` uses the `bcrypt` package directly), and the extra dependency was never declared. It only ever worked because passlib happened to be present in the author's environment. Additionally, passlib 1.7.x is incompatible with `bcrypt>=4.1` (the pinned range here), which errors even when passlib *is* installed.
**Impact:** `python scripts/seed.py` crashes with `ModuleNotFoundError` on any clean install, CI runner, or fresh Docker container — the documented onboarding path ("Seed sample data") is broken for every new developer.
**Fix:** Replace passlib with the app's own `app.core.security.hash_password`; delete the `pwd_context`.

## High severity — already fixed (but the mistake was made)

### 3. Enum columns stored Python member names, not values ✅
**Where (fix):** all five model files — `SAEnum(..., values_callable=lambda obj: [e.value for e in obj])`; recorded in `docs/codebase/CONCERNS.md`.
**Mistake:** Initial models omitted `values_callable`, so SQLAlchemy sent `STUDENT`/`IN_COLLEGE` while the Supabase enum types held `student`/`in_college`.
**Impact:** Inserts/updates failed against the real database at runtime — a class of bug invisible to the mocked unit suite, discovered only against Supabase. Cost a production-debugging session; the reason the rule is now written down everywhere.

### 4. JWT blacklist was an in-memory `set()` ✅
**Where (fix):** `app/services/auth.py` — now Redis `SETEX bl:<token>` with in-memory fallback.
**Mistake:** Token revocation state was per-process and volatile.
**Impact:** Logout/rotation revocation silently didn't work across workers, and every deploy un-revoked all tokens. A revoked (stolen) refresh token stayed usable on any other worker for up to 7 days.

---

## Medium severity — open

### 5. Logout doesn't revoke access tokens
**Where:** `app/services/auth.py:172-174` — `logout()` blacklists only the refresh token. Meanwhile `get_current_user` (`app/api/deps.py`) dutifully checks the blacklist for every access token — a check that can never hit, because nothing ever blacklists an access token.
**Mistake:** Inconsistent design: the expensive infrastructure (a Redis GET per authenticated request) exists precisely to support immediate revocation, but the one operation users think of as revocation ("log out") leaves the access token valid.
**Impact:** For up to 15 minutes after logout, the access token still works on every endpoint. If a user logs out because their token leaked, the attacker keeps full API access until expiry. Also: one wasted Redis round-trip on every authenticated request.
**Fix:** Have `/auth/logout` accept (or read from the Authorization header) the access token and blacklist it with a TTL equal to its remaining life — the checking side already exists.

### 6. Registration capacity and duplicate checks are check-then-act races
**Where:** `app/services/registration.py:30-49` — `SELECT count(...)` then later `INSERT`; `SELECT` for existing registration then `INSERT`.
**Mistake:** No locking (`SELECT ... FOR UPDATE` on the event row) and no `IntegrityError` handling around the insert.
**Impact:** Two concurrent registrations for the last slot both pass the capacity check → event oversold past `max_registrations`. Two identical concurrent registrations both pass the duplicate check → the DB unique constraint `uq_reg_event_student_role` fires → unhandled `IntegrityError` → the client gets a 500 `INTERNAL_ERROR` instead of the intended 409, and the error log gets a spurious stack trace. For a college event system, registration-open moments are exactly when concurrent bursts happen.
**Fix:** Lock the event row (`with_for_update()`) for the capacity path; catch `IntegrityError` and re-raise `ConflictException` for the duplicate path.

### 7. Attendance bulk-mark is an N+1 loop
**Where:** `app/services/attendance.py:48-70` — for each of up to 100 records: one `SELECT` for the existing row, then update-or-add.
**Mistake:** The unique constraint `uq_att_event_student_date` exists precisely to support a single `INSERT ... ON CONFLICT DO UPDATE`; instead the service does up to 100 sequential SELECTs plus inserts over a PgBouncer connection.
**Impact:** A full-class attendance call issues ~101 round trips to a pooled Supabase connection — the slowest and most drop-prone pattern possible here (PgBouncer connection drops under load are already a documented concern). Also the same TOCTOU shape as #6: two coordinators marking simultaneously → `IntegrityError` → 500.
**Fix:** One `pg_insert(...).on_conflict_do_update(constraint="uq_att_event_student_date", ...)` with all rows.

### 8. Config settings that are read by no one
**Where:** `app/core/security.py:9` hardcodes `ALGORITHM = "HS256"` and ignores `settings.JWT_ALGORITHM`; `app/core/database.py:14-18` never passes `DATABASE_POOL_SIZE` / `DATABASE_MAX_OVERFLOW` to `create_async_engine`.
**Mistake:** Settings were declared (and documented in `.env.example`) without wiring them to the code they claim to control.
**Impact:** An operator who "tunes the pool to 20 connections" or "switches the JWT algorithm" via env vars changes nothing, silently. Debugging time is lost on configuration that is theater. The engine actually runs with SQLAlchemy defaults (pool_size 5, max_overflow 10) — different from *both* documented value sets.
**Fix:** Either wire the settings through or delete them; don't leave dead knobs.

### 9. Rate limiting keyed by direct client IP
**Where:** `app/middleware/rate_limit.py` — key `rl:{request.client.host}:{path}`.
**Mistake:** No `X-Forwarded-For` handling. Behind any reverse proxy or load balancer (i.e., every realistic deployment), `client.host` is the proxy's IP.
**Impact:** All real users share one 100 req/min bucket per path — the whole college gets rate-limited as a single client during peak use (event registration opening). Conversely, an attacker who can vary the direct source (or when the app is exposed directly) is limited per-IP as intended, so the control fails exactly in the deployment mode it's meant for.
**Fix:** Trust a configurable forwarded-IP header when behind a proxy (uvicorn `--proxy-headers` + `request.client` or explicit header parsing).

### 10. Unbounded in-memory fallbacks
**Where:** `app/services/auth.py:22` (`_blacklisted_tokens_fallback: set` — entries never expire) and `app/middleware/rate_limit.py:12-23` (`InMemoryRateLimiter` per-key lists pruned only when that key is re-checked).
**Mistake:** The fallbacks replicate Redis's behavior but not its TTLs.
**Impact:** In a long-running Redis-less deployment, blacklisted tokens accumulate forever (memory leak + ever-growing set membership checks), and one-off scanned paths leave rate-limit keys behind permanently. Slow-burn memory growth that surfaces as an OOM weeks later with no obvious cause.
**Fix:** Store `(token, expiry)` and prune on access, or cap the structures.

### 11. Two incompatible response-envelope conventions
**Where:** `app/schemas/event.py` and `app/schemas/users.py` inline `success: bool` and flat pagination (`items`/`users`, `total/page/limit/total_pages` at top level); everything newer uses `schemas/common.py` generics (`{"success", "data", "meta": {...}}`).
**Mistake:** The generic envelope was introduced mid-project and the earlier modules were never migrated (nor was the divergence documented at the time).
**Impact:** A frontend cannot write one pagination handler — events/users lists parse differently from registrations/attendance/notifications lists. Every new client integration rediscovers this and pays for it; the API contract is inconsistent with its own docs unless each shape is separately documented (it now is, in `docs/api-specification.md`, at the cost of doubled documentation).
**Fix:** Migrate events/users to `common.py` envelopes behind a version bump, or freeze and document — but decide once.

## Medium severity — already fixed

### 12. Dependency added to only one manifest ✅ (commit `36ce2e5`)
**Mistake:** New dependencies went into `requirements.txt` but not `pyproject.toml`.
**Impact:** `pytest` broke for anyone installing via the project metadata; CI and local disagreed about the environment. Now codified as the Two-Manifest Rule in `CLAUDE.md`.

### 13. Dashboard executed 8 aggregate queries sequentially ✅
**Where (fix):** `app/services/reports.py` — now `asyncio.gather`.
**Impact:** Dashboard latency was the sum of 8 round trips to a remote pooled Postgres (~8× worse than necessary); the fix made it max-of-8.

### 14. Model/database schema drift on `coordinator_id` ✅
**Mistake:** The live Supabase column was `NOT NULL` while the model declared `nullable=True` — the DB was altered directly at some point without a migration.
**Impact:** Creating an event without a coordinator raised `IntegrityError` (500) despite the model saying it was legal. Fixed with a direct `ALTER TABLE ... DROP NOT NULL` in Supabase — which is itself a process mistake: the fix bypassed Alembic, so a rebuilt-from-migrations database and the live database can still disagree. The migration chain was never repaired.

### 15. Test-suite flakiness from module reloading ✅ (commit `585c09d`)
**Mistake:** `test_config.py` deleted and re-imported `app.core.*` modules per test, so exception classes raised by app code were *different class objects* than the ones other tests imported — `pytest.raises` failed nondeterministically depending on test order.
**Impact:** Intermittent red CI unrelated to actual changes; hours lost re-running. Fixed by snapshotting and restoring `sys.modules` entries. The same hazard still lives in `test_e2e_workflows.py` (purges all `app.*` modules), which is why e2e must never be interleaved with the unit suite.

---

## Low severity — open

### 16. `reject_teacher` accepts ACTIVE teachers
**Where:** `app/services/user.py` — `approve_teacher` guards against both ACTIVE and REJECTED; `reject_teacher` only guards against REJECTED.
**Impact:** An admin can "reject" an already-approved, working teacher through the pending-teachers workflow; the teacher silently loses login (`status != active` → 403 at login) with a notification implying their *application* was rejected. Probably intended as deactivation, but asymmetric with the approve path and untested as such.

### 17. `AttendanceStatus.LATE` is dead
**Where:** enum in `app/models/attendance.py`; the only write path (`mark_bulk`, `app/services/attendance.py:49`) maps `present: bool` → PRESENT/ABSENT.
**Impact:** Schema, migration, DB enum type, and docs all advertise a three-state attendance model the API cannot produce. Dashboards/report consumers coded against `late` will never see it; the value is a trap for future developers.

### 18. Timezone-naive date validation
**Where:** `app/services/event.py:81-82` — `data.start_date.date() < date.today()` compares the date component of a client-supplied tz-aware datetime against the *server's local* date.
**Impact:** Near midnight or across timezones, "today" events are wrongly rejected (or yesterday's accepted). Off-by-one-day behavior that will be reported as an unreproducible bug because it depends on server locale and time of day.
**Fix:** Compare in UTC: `data.start_date.astimezone(timezone.utc).date() < datetime.now(timezone.utc).date()`.

### 19. Legacy `HTTPException` in auth/user services
**Where:** `app/services/auth.py`, `app/services/user.py` — inline `from fastapi import HTTPException` raises.
**Impact:** These errors bypass the `AppHTTPException` handler, so their bodies are `{"success": false, "error": {"code": "HTTP_ERROR"|"NOT_FOUND", "message": ...}}` via the Starlette fallback handler — error `code` strings are inconsistent with the rest of the API (`UNAUTHORIZED`, `CONFLICT`, etc. are missing exactly on the auth endpoints, where clients most need to branch on them). Also couples business logic to the HTTP layer, against the project's own layering rule.

### 20. Hand-rolled email validation
**Where:** `app/schemas/auth.py` — checks "contains `@` and `.`" and `endswith("@college.edu")` instead of Pydantic's `EmailStr`.
**Impact:** Accepts malformed addresses like `"a@b@college.edu"` or whitespace-embedded strings that a real validator rejects; the unique index then permanently stores junk identities. Low today, annoying the day email delivery is added.

### 21. Blacklist keys embed the full JWT with a flat 7-day TTL
**Where:** `app/services/auth.py:24, 167` — key `bl:<entire-token>`, TTL always `JWT_REFRESH_EXPIRE_DAYS * 86400`.
**Impact:** Keys are ~500+ bytes each (whole signed token as key material) and every rotated refresh token is stored for a full 7 days even if it had 1 hour of validity left. On a free-tier Upstash (10 MB — the documented production plan), an active user base rotating tokens can consume the entire quota with revocation records. Store `sha256(token)` and use the token's actual remaining TTL.

### 22. bcrypt 72-byte truncation vs. 100-char password limit
**Where:** `app/core/security.py:52-54` (`bcrypt.hashpw`), `app/schemas/auth.py` (password `max_length=100`).
**Impact:** Characters beyond 72 bytes are silently ignored — two passwords differing only after byte 72 authenticate interchangeably. Cosmetic for most users, but it contradicts the advertised 100-char limit and surprises security review.

### 23. `.env.example` disagrees with `config.py` defaults
**Where:** `.env.example` says pool 10/20; `config.py` defaults 5/3; neither reaches the engine (see #8).
**Impact:** Three different "truths" about pool sizing. Documentation debt that compounds mistake #8.

### 24. Live-DB tests are collected by default and fail hard
**Where:** `pyproject.toml` `testpaths=["tests"]` includes `tests/real_db/`; `tests/real_db/conftest.py` builds an engine from `settings.DATABASE_URL` with no skip-if-unreachable marker.
**Impact:** `pytest tests/` (a natural invocation) attempts to connect to the production Supabase instance from any developer machine; without credentials it errors (noise), *with* credentials it silently exercises the live DB. The convention "run it only by explicit path" exists only in docs, not in the tooling. A `pytest.mark.real_db` + `addopts` exclusion (mirroring `e2e`) would make the safety structural.

### 25. Double-commit pattern
**Where:** `app/core/database.py:27-36` (`get_db` commits on success) *and* every service commits explicitly.
**Impact:** Harmless today (second commit is a no-op) but ambiguous ownership: a future service that intentionally defers commit will be surprised by the dependency committing anyway, and error-path semantics (service committed, later router code raises → `get_db` rollback does nothing) are easy to misread. Pick one owner. The project has since standardized on "services own commits" — the dependency's commit should go.

### 26. Deprecated security header
**Where:** `app/middleware/security.py` — `X-XSS-Protection: 1; mode=block`.
**Impact:** None functionally (modern browsers ignore it; some old-Edge configurations had vulnerabilities *because* of it). Pure cargo-cult residue; remove on next touch.

---

## 27. Not mistakes — recorded decisions 📋

Listed so nobody "fixes" them and so they aren't attributed as oversights (see
`docs/codebase/CONCERNS.md` → Resolved Decisions):

- **No linter / formatter / pre-commit hooks** — explicitly declined.
- **`/health` does not ping DB/Redis** — explicitly declined; it is a liveness probe only.
- **Startup swallows DB connection failure** (warns, boots anyway) — consistent with the
  shallow-health decision; the app is allowed to start before its database.
- **No repository layer** — accepted trade-off (documented), paid for in mock complexity (see The Mock Chain Rule in `CLAUDE.md`).
- **Redis optional with in-memory degradation** — deliberate for dev ergonomics; the
  *unbounded* fallbacks (#10) are the mistake, not the fallback itself.

---

## Aggregate assessment

The recurring failure patterns, in order of damage caused:

1. **Trusting the mocked test suite as proof of production behavior** — #3, #14, and partly
   #6/#7 were all invisible to `AsyncMock`-based tests and only exist against a real
   Postgres. 97% coverage measured the mocks, not the database contract.
2. **Declaring without wiring** — #8, #23 (settings), #17 (enum value), #5 (blacklist check
   with no writer): infrastructure built on one side and never connected on the other.
3. **Concurrency blindness** — #6, #7, #10, and historically #4: everything works for one
   user on one worker; the failure modes need two simultaneous requests or two processes.
4. **Process shortcuts around the database** — #14's direct-in-Supabase fix left the
   migration chain unable to reproduce production; #2 shows scripts never re-run in a clean
   environment.

The corresponding preventive rules are already encoded in `CLAUDE.md` (Failure Modes #2, #5,
#7, #8, #9) and the `/db-migration` and `/verify` skills; items marked 🔴 above are the
outstanding remediation backlog, ordered by the summary table.
