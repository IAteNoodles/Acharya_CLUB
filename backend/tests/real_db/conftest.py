import asyncio
import sys
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool
from testcontainers.postgres import PostgresContainer

from app.models.user import User, Role, UserStatus
from app.models.base import Base

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

pytestmark = pytest.mark.asyncio


@pytest.fixture(scope="session")
def pg_container():
    with PostgresContainer("postgres:16-alpine") as pg:
        yield pg


@pytest.fixture(scope="session")
def async_engine(pg_container):
    db_url = pg_container.get_connection_url(driver="asyncpg")

    sync_url = db_url.replace("+asyncpg", "")
    sync_engine = create_engine(sync_url)
    import app.models.user  # noqa
    import app.models.event  # noqa
    import app.models.registration  # noqa
    import app.models.attendance  # noqa
    import app.models.notification  # noqa
    Base.metadata.create_all(sync_engine)
    sync_engine.dispose()

    engine = create_async_engine(db_url, echo=False, poolclass=NullPool)
    yield engine
    engine.sync_engine.dispose()


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
