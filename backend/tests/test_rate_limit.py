import pytest
from fakeredis import FakeAsyncRedis
from fastapi import Depends
from httpx import ASGITransport, AsyncClient


# ── In-memory fallback rate limiter tests ────────────


@pytest.mark.asyncio
async def test_under_limit_passes():
    from fastapi import FastAPI
    from app.middleware.rate_limit import get_rate_limiter

    app = FastAPI()
    limiter = await get_rate_limiter(max_requests=5, window_seconds=60, redis_client=None)

    @app.get("/test")
    async def test_endpoint(_=Depends(limiter)):
        return {"ok": True}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for _ in range(5):
            resp = await client.get("/test")
            assert resp.status_code == 200


@pytest.mark.asyncio
async def test_over_limit_blocked():
    from fastapi import FastAPI
    from app.middleware.rate_limit import get_rate_limiter

    app = FastAPI()
    limiter = await get_rate_limiter(max_requests=3, window_seconds=60, redis_client=None)

    @app.get("/test")
    async def test_endpoint(_=Depends(limiter)):
        return {"ok": True}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for _ in range(3):
            resp = await client.get("/test")
            assert resp.status_code == 200

        resp = await client.get("/test")
        assert resp.status_code == 429


# ── Redis-backed rate limiter tests ─────────────────


@pytest.fixture
def fake_redis():
    return FakeAsyncRedis(decode_responses=True)


@pytest.mark.asyncio
async def test_redis_under_limit_passes(fake_redis):
    from fastapi import FastAPI
    from app.middleware.rate_limit import get_rate_limiter

    app = FastAPI()
    limiter = await get_rate_limiter(max_requests=5, window_seconds=60, redis_client=fake_redis)

    @app.get("/test")
    async def test_endpoint(_=Depends(limiter)):
        return {"ok": True}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for _ in range(5):
            resp = await client.get("/test")
            assert resp.status_code == 200


@pytest.mark.asyncio
async def test_redis_over_limit_blocked(fake_redis):
    from fastapi import FastAPI
    from app.middleware.rate_limit import get_rate_limiter

    app = FastAPI()
    limiter = await get_rate_limiter(max_requests=3, window_seconds=60, redis_client=fake_redis)

    @app.get("/test")
    async def test_endpoint(_=Depends(limiter)):
        return {"ok": True}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for _ in range(3):
            resp = await client.get("/test")
            assert resp.status_code == 200

        resp = await client.get("/test")
        assert resp.status_code == 429


@pytest.mark.asyncio
async def test_redis_different_keys_independent(fake_redis):
    from fastapi import FastAPI
    from app.middleware.rate_limit import get_rate_limiter

    app = FastAPI()
    limiter = await get_rate_limiter(max_requests=2, window_seconds=60, redis_client=fake_redis)

    @app.get("/a")
    async def endpoint_a(_=Depends(limiter)):
        return {"ok": True}

    @app.get("/b")
    async def endpoint_b(_=Depends(limiter)):
        return {"ok": True}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for _ in range(2):
            resp = await client.get("/a")
            assert resp.status_code == 200

        resp = await client.get("/a")
        assert resp.status_code == 429

        resp = await client.get("/b")
        assert resp.status_code == 200
        resp = await client.get("/b")
        assert resp.status_code == 200
