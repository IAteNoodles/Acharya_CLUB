import pytest

pytestmark = pytest.mark.asyncio


async def test_get_redis_returns_none_when_no_url(monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.delenv("UPSTASH_REDIS_REST_URL", raising=False)
    monkeypatch.delenv("UPSTASH_REDIS_REST_TOKEN", raising=False)
    import importlib
    from app.core import redis as redis_module
    importlib.reload(redis_module)

    client = await redis_module.get_redis()
    assert client is None
    redis_module._redis_instance = None


async def test_close_redis_does_not_raise_when_no_instance(monkeypatch):
    import importlib
    from app.core import redis as redis_module

    redis_module._redis_instance = None
    importlib.reload(redis_module)

    await redis_module.close_redis()
    assert redis_module._redis_instance is None


async def test_get_redis_returns_cached_instance(monkeypatch):
    from app.core import redis as redis_module

    redis_module._redis_instance = "already-connected"

    client = await redis_module.get_redis()
    assert client == "already-connected"
    redis_module._redis_instance = None


async def test_get_redis_upstash_init(monkeypatch):
    monkeypatch.setenv("UPSTASH_REDIS_REST_URL", "https://upstash.example.com")
    monkeypatch.setenv("UPSTASH_REDIS_REST_TOKEN", "test-token")
    import importlib
    from app.core import redis as redis_module

    redis_module._redis_instance = None
    importlib.reload(redis_module)

    client = await redis_module.get_redis()
    assert client is not None
    assert hasattr(client, "url") or hasattr(client, "_url")
    redis_module._redis_instance = None


async def test_get_redis_redis_url_init(monkeypatch):
    monkeypatch.delenv("UPSTASH_REDIS_REST_URL", raising=False)
    monkeypatch.delenv("UPSTASH_REDIS_REST_TOKEN", raising=False)
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/1")
    import importlib
    from app.core import redis as redis_module

    redis_module._redis_instance = None
    importlib.reload(redis_module)

    client = await redis_module.get_redis()
    assert client is not None
    redis_module._redis_instance = None
