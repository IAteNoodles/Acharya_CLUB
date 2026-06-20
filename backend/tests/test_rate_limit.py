import pytest
from fastapi import Depends
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_under_limit_passes():
    from fastapi import FastAPI
    from app.middleware.rate_limit import get_rate_limiter

    app = FastAPI()
    limiter = await get_rate_limiter(max_requests=5, window_seconds=60)

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
    limiter = await get_rate_limiter(max_requests=3, window_seconds=60)

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
