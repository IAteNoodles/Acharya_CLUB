import os

import pytest


@pytest.fixture(autouse=True)
def set_env():
    os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/test")
    os.environ.setdefault("JWT_SECRET", "a" * 32)
    yield


def test_engine_created():
    from app.core.database import engine

    assert engine is not None
    assert str(engine.url) != ""


@pytest.mark.asyncio
async def test_database_module_imports():
    from app.core.database import get_db, async_session_factory

    assert get_db is not None
    assert async_session_factory is not None
