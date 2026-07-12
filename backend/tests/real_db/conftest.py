import asyncio
import sys
import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from app.models.user import User, Role, UserStatus
from app.models.base import Base

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

pytestmark = pytest.mark.asyncio


@pytest.fixture(scope="session")
def async_engine():
    db_url = "sqlite+aiosqlite:///:memory:"

    import app.models.user  # noqa: F401
    import app.models.event  # noqa: F401
    import app.models.registration  # noqa: F401
    import app.models.attendance  # noqa: F401
    import app.models.notification  # noqa: F401

    engine = create_async_engine(
        db_url,
        echo=False,
    )

    async def _bootstrap():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_bootstrap())

    yield engine

    async def _cleanup():
        await engine.dispose()

    asyncio.run(_cleanup())


@pytest_asyncio.fixture
async def db_session(async_engine):
    conn = await async_engine.connect()
    trans = await conn.begin()

    session = AsyncSession(bind=conn, expire_on_commit=False)

    # Override commit → flush so tests never permanently commit
    async def _flush_only():
        await session.flush()

    session.commit = _flush_only

    yield session

    await session.close()
    await trans.rollback()
    await conn.close()


@pytest_asyncio.fixture
async def admin_user(db_session):
    user = User(
        name="Admin",
        email=f"admin.{uuid.uuid4()}@college.edu",
        password_hash="hash",
        role=Role.ADMIN,
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def teacher_user(db_session):
    user = User(
        name="Teacher",
        email=f"teacher.{uuid.uuid4()}@college.edu",
        password_hash="hash",
        role=Role.TEACHER,
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def student_user(db_session):
    user = User(
        name="Student",
        email=f"student.{uuid.uuid4()}@college.edu",
        password_hash="hash",
        role=Role.STUDENT,
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user
