import asyncio
import sys
import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.models.user import User, Role, UserStatus
from app.models.base import Base

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

pytestmark = pytest.mark.asyncio


@pytest.fixture(scope="session")
def async_engine():
    db_url = settings.DATABASE_URL

    import app.models.user
    import app.models.event
    import app.models.registration
    import app.models.attendance
    import app.models.notification

    engine = create_async_engine(db_url, echo=False, poolclass=NullPool, connect_args={"statement_cache_size": 0})

    async def _probe():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_probe())

    yield engine

    async def _cleanup():
        await engine.dispose()

    asyncio.run(_cleanup())


@pytest_asyncio.fixture
async def db_session(async_engine):
    conn = await async_engine.connect()
    trans = await conn.begin()

    session = AsyncSession(bind=conn, expire_on_commit=False)

    async def _commit():
        await session.flush()
    session.commit = _commit

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
