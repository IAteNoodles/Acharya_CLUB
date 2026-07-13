---
name: db-migration
description: Create, test, and apply an Alembic migration for this repo's Supabase Postgres — hand-written numeric revisions, PG enum handling (values_callable, DROP TYPE in downgrade), PgBouncer constraints, and safe verification against a scratch DB before touching Supabase. Use for any schema change (new table, column, enum, index, constraint).
---

# Database Migration (Alembic + Supabase)

This repo hand-writes migrations. **Never** run `alembic revision --autogenerate` — the
existing migrations were authored by hand and autogenerate will fight the enum setup and
naming conventions. Work from `backend/`.

## Ground rules

1. **Revision IDs are numeric strings** in a linear chain: `"0001"` → `"0002"` → yours is
   the next number. Filename: `alembic/versions/000N_<slug>.py`. Set `down_revision` to the
   current head (check with `alembic heads` or read the latest version file).
2. **The model is the contract.** Write the model first (UUID PK + timestamps come from
   `TimestampMixin`), then make the migration match it column-for-column, constraint-name
   for constraint-name (`uq_*`, `*_idx`).
3. **Model must be imported in `alembic/env.py`** (add to the explicit import block) and
   re-exported in `app/models/__init__.py`, or metadata won't see it.
4. The DB URL comes from `settings.DATABASE_URL` via `env.py` — `alembic.ini` has no URL.
   Whatever `.env` points at is what `alembic upgrade head` migrates. **Check `.env` before
   running anything.**

## Postgres enum handling (the #1 source of past bugs here)

- Python enums are `(str, enum.Enum)` with **lowercase snake_case values**; the DB enum type
  stores the *values*. The model column MUST use
  `SAEnum(MyEnum, values_callable=lambda obj: [e.value for e in obj])` — without it,
  SQLAlchemy writes member NAMES (`STUDENT`) and inserts fail against the Supabase types.
- In the migration, declare the enum with lowercase values and a lowercase type name
  (SQLAlchemy's default derived name, e.g. `notificationtype`):

```python
sa.Column(
    "status",
    sa.Enum("pending", "active", "rejected", name="mystatus"),
    nullable=False,
    server_default="pending",
)
```

- **`downgrade()` must drop every enum type the migration created** — Postgres does not drop
  enum types with their table:

```python
def downgrade() -> None:
    op.drop_table("my_table")
    op.execute("DROP TYPE IF EXISTS mystatus")
```

- Adding a value to an existing enum: `op.execute("ALTER TYPE mystatus ADD VALUE 'newval'")`.
  Caveats: it cannot run inside a transaction block on older PG (use
  `with op.get_context().autocommit_block():`), and enum values **cannot be removed** — the
  downgrade for an added value is a no-op with a comment saying so.

## Table template (matches TimestampMixin)

```python
revision = "000N"
down_revision = "000M"

def upgrade() -> None:
    op.create_table(
        "<x>s",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id"), nullable=False),
        # ... domain columns ...
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("event_id", "student_id", name="uq_<x>_event_student"),
    )
    op.create_index("<x>_user_id_idx", "<x>s", ["user_id"])
```

## Verification procedure (scratch DB FIRST, Supabase last)

Never test a new migration against Supabase directly. Use the compose local-db profile:

```bash
# 1. Start scratch Postgres
docker compose --profile local-db up -d postgres

# 2. Point Alembic at it for this shell only
export DATABASE_URL='postgresql+asyncpg://postgres:localdev@localhost:5432/acharya'

# 3. Round-trip: up → down → up must all succeed
alembic upgrade head
alembic downgrade -1
alembic upgrade head

# 4. Confirm enum types survived the round trip (no orphans)
docker compose exec postgres psql -U postgres -d acharya -c "\dT+"

# 5. Model/DB agreement: boot the app's metadata against it
python -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.models.base import Base
import app.models.user, app.models.event, app.models.registration, app.models.attendance, app.models.notification  # noqa
async def check():
    e = create_async_engine('$DATABASE_URL')
    async with e.connect() as c:
        def cmp(sync_conn):
            from sqlalchemy import inspect
            insp = inspect(sync_conn)
            for t in Base.metadata.tables:
                assert insp.has_table(t), f'missing table {t}'
        await c.run_sync(cmp)
    await e.dispose()
    print('model/DB tables OK')
asyncio.run(check())
"

# 6. Unit suite still green
unset DATABASE_URL && pytest -v
```

Only after all six pass, apply to Supabase: restore the real `.env`, run
`alembic upgrade head`, and confirm with `alembic current`.

## Supabase/PgBouncer constraints to respect

- Connections go through PgBouncer (transaction pooling): asyncpg needs
  `statement_cache_size=0` (already set where it matters — don't remove it) and long
  DDL can hit transient `ConnectionDoesNotExistError`; if a migration fails mid-flight,
  check `alembic current` before re-running.
- Some past schema drift was fixed directly in Supabase (e.g.
  `ALTER TABLE events ALTER COLUMN coordinator_id DROP NOT NULL`) — if the live DB
  disagrees with migration files, check `docs/codebase/CONCERNS.md` before "fixing" it.
- Docker prod entrypoint auto-runs `alembic upgrade head` at container start and only WARNS
  on failure — a broken migration won't stop the container, it will surface as runtime
  errors. Test the round trip locally precisely because of this.

## Done-check

- [ ] `alembic upgrade head && alembic downgrade -1 && alembic upgrade head` clean on scratch DB
- [ ] `downgrade()` drops every enum type created in `upgrade()`
- [ ] Constraint/index names match the model's `__table_args__` exactly (`uq_*`, `*_idx`)
- [ ] Model imported in `alembic/env.py` + re-exported in `app/models/__init__.py`
- [ ] Every enum column in the model has `values_callable`
- [ ] `pytest -v` green
- [ ] `docs/database-schema.md` updated
- [ ] Commit: `feat(<x>): add migration 000N_<slug>` (or `fix(db): ...`)
