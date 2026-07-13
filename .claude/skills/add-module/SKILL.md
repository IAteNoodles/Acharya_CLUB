---
name: add-module
description: Scaffold a complete new domain module (model → migration → schemas → service → router → tests → registration → notifications → docs) following this repo's exact layering, conventions, and commit discipline. Use whenever adding a new entity/feature area to the backend (e.g. "add a feedback module", "add event comments").
---

# Add a Domain Module

Build the module in the exact order below. **One conventional commit per step.** Work from
`backend/`. The newest modules (notifications, reports) are the style exemplars — when in
doubt, open `app/models/notification.py`, `app/services/notification.py`,
`app/api/v1/notifications.py`, `tests/test_notifications.py` and mirror them.

If the user hasn't specified the design, first write a short design spec to
`docs/superpowers/specs/<YYYY-MM-DD>-<module>-design.md` (endpoints, schemas, service
methods, file map — see `docs/superpowers/specs/2026-06-21-reports-design.md` for size and
shape) and confirm the endpoint/role matrix with the user before writing code.

Throughout: no docstrings, absolute `app.` imports, `_`-prefixed helpers at the bottom of
router files, no linter config. Placeholder `<x>` = snake_case module name, `<X>` = PascalCase.

## Step 1 — Model + enums (`app/models/<x>.py`)

```python
import enum
import uuid

from sqlalchemy import Enum as SAEnum, ForeignKey, String, Text, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class <X>Status(str, enum.Enum):
    PENDING = "pending"     # lowercase snake_case VALUES — the DB stores values
    ...


class <X>(TimestampMixin, Base):
    __tablename__ = "<x>s"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    status: Mapped[<X>Status] = mapped_column(
        SAEnum(<X>Status, values_callable=lambda obj: [e.value for e in obj]),  # MANDATORY
        default=<X>Status.PENDING,
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("...", name="uq_<x>_..."),   # uq_* naming
        Index("<x>_..._idx", "..."),                  # *_idx naming
    )
```

Then:
- Re-export the model and enums in `app/models/__init__.py`.
- Add `from app.models import <x>  # noqa` to the model-import block in `alembic/env.py`.

Verify: `python -c "from app.models.<x> import <X>; print('OK')"`
Commit: `feat(<x>): add <X> model + <X>Status enum`

## Step 2 — Migration

Invoke the `/db-migration` skill for the full procedure (numeric revision, PG enum
creation, downgrade drops enum types, scratch-DB round-trip test). Do not autogenerate.

Commit: `feat(<x>): add migration 000N_<x>`

## Step 3 — Schemas (`app/schemas/<x>.py`)

Pydantic v2. Use `schemas/common.py` envelopes — do NOT copy the bespoke envelopes in
`schemas/event.py` / `schemas/users.py` (legacy style).

```python
import uuid
from pydantic import BaseModel, Field, field_validator


class <X>CreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    # request IDs: uuid.UUID type, or str + uuid.UUID(v) in a field_validator


class <X>Out(BaseModel):
    model_config = {"from_attributes": True}
    id: str
    status: str
    # enums serialize as their .value strings; IDs as str
```

Responses at the router use `SuccessResponse[<X>Out]` and `PaginatedResponse` with nested
`meta: PaginatedMeta` from `app/schemas/common.py`.

Verify: `python -c "from app.schemas.<x> import <X>Out; print('OK')"`
Commit: `feat(<x>): add Pydantic schemas`

## Step 4 — Service + tests (SAME commit)

`app/services/<x>.py`:

```python
class <X>Service:
    @staticmethod
    async def create_<x>(db: AsyncSession, data: <X>CreateRequest, current_user: dict):
        from app.core.exceptions import ConflictException, ForbiddenException, NotFoundException
        # current_user is the JWT payload dict: current_user["sub"], current_user["role"]
        # raise AppHTTPException subclasses — NEVER fastapi.HTTPException
        # authorization: compare current_user["sub"]/["role"] against rows
        ...
        db.add(obj)
        await db.commit()      # services own their commit
        await db.refresh(obj)
        return obj
```

Rules:
- `@staticmethod async def`, `db: AsyncSession` first param.
- Every state change another user should know about → `NotificationService.create_notification`
  (add a `NotificationType` value + template + migration if a new type is needed).
- Pagination helpers: copy the `_compute_pagination` pattern from `services/user.py`.

Tests in `tests/test_<x>.py`, class `Test<X>Service`, module has the right async marking:

```python
pytestmark = pytest.mark.asyncio

class Test<X>Service:
    async def test_create_<x>_success(self):
        db = AsyncMock()
        db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        result = await <X>Service.create_<x>(db, data, {"sub": str(uuid.uuid4()), "role": "student"})
        db.commit.assert_called_once()

    async def test_create_<x>_forbidden(self):
        with pytest.raises(ForbiddenException, match="..."):
            ...
```

Mock-chain reference (must mirror the service's real queries, in order):
- list query → `MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[...]))))`
- single row → `MagicMock(scalar_one_or_none=MagicMock(return_value=obj))`
- count → `db.scalar.return_value = n`
- pk fetch → `db.get.return_value = obj` (AsyncMock)
- multiple queries → `db.execute.side_effect = [r1, r2, ...]`
- Every authorization branch and every raise gets its own test.

Verify: `pytest tests/test_<x>.py -v`
Commit: `feat(<x>): add <X>Service with tests`

## Step 5 — Router + API tests (SAME commit)

`app/api/v1/<x>.py`:

```python
router = APIRouter(prefix="/api/v1/<x>s", tags=["<x>s"])   # router owns its prefix

@router.post("", status_code=201)
async def create_<x>(
    data: <X>CreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_student),   # pick the right guard per endpoint
):
    obj = await <X>Service.create_<x>(db, data, current_user)
    return SuccessResponse(data=_<x>_to_out(obj))

# _helpers at the bottom; convert enums via `v.value if hasattr(v, "value") else v`
```

Pagination params: `page: int = Query(1, ge=1)`, `limit: int = Query(20, ge=1, le=100)`.

API tests, class `Test<X>API` — throwaway app pattern:

```python
def _make_app(user=None):
    app = FastAPI()
    app.include_router(router)
    register_exception_handlers(app)          # required if you assert error bodies
    if user:
        app.dependency_overrides[deps.get_current_user] = lambda: user
    return app
```

Required negative tests: 401 with no override/token; 403 for each wrong role; error body
`data["error"]["code"]` assertions for 404/409/422 paths. Patch the service at module path
(`patch("app.services.<x>.<X>Service.create_<x>")`).

Verify: `pytest tests/test_<x>.py -v`
Commit: `feat(<x>): add <x> router + API tests`

## Step 6 — Register in `app/main.py`

- Import the router in `create_app()`, `app.include_router(<x>_router)` (no prefix arg).
- Add `{"name": "<x>s", "description": "..."}` to `openapi_tags`.

Verify (endpoint appears with BearerAuth):
`python -c "from app.main import create_app; import json; spec = create_app().openapi(); assert any('/<x>s' in p for p in spec['paths']); print('OK')"`
Commit: `feat(<x>): register <x> router + OpenAPI tag`

## Step 7 — Notification integrations (if applicable)

One commit per workflow integrated (see `git log` for the notifications module: separate
commits for registration accept/reject, event approve/reject, teacher approve/reject).
Each integration test asserts `mock_create.assert_awaited_once()` with the right type.

## Step 8 — Docs (final commit)

Update, in this order:
1. `docs/api-specification.md` — full endpoint contracts.
2. `docs/database-schema.md` — if schema changed.
3. `README.md` (root) + `backend/README.md` — endpoint tables, counts ("7 services" etc.).
4. `docs/codebase/STRUCTURE.md` / `ARCHITECTURE.md` — file lists and counts.
5. Move the spec's plan to `docs/superpowers/plans/` if you wrote one.

Commit: `docs: add <x> module docs and update API reference`

## Done-check (all must pass)

```bash
cd backend
pytest -v                                        # zero failures
pytest --cov=app --cov-report=term-missing       # new files fully covered, total ≥97%
python -c "from app.main import create_app; create_app(); print('app boots OK')"
```

And: no `fastapi.HTTPException` in the new service; every SAEnum has `values_callable`;
router registered; both manifests updated if deps changed; docs committed.
