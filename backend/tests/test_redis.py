import pytest

pytestmark = pytest.mark.asyncio


async def test_get_redis_returns_none_when_no_url(monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)
    import importlib
    from app.core import redis as redis_module
    importlib.reload(redis_module)

    client = await redis_module.get_redis()
    assert client is None
    redis_module._redis_instance = None
