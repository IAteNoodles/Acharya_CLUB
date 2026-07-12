import asyncio

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_timeout_middleware_passes_fast_requests():
    from fastapi import FastAPI
    from app.middleware.timeout import RequestTimeoutMiddleware

    app = FastAPI()
    app.add_middleware(RequestTimeoutMiddleware, timeout_seconds=30)

    @app.get("/fast")
    async def fast():
        return {"ok": True}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/fast")

    assert resp.status_code == 200
    assert resp.json()["ok"] is True


@pytest.mark.asyncio
async def test_timeout_middleware_returns_503_on_slow_request():
    from fastapi import FastAPI
    from app.middleware.timeout import RequestTimeoutMiddleware

    app = FastAPI()
    app.add_middleware(RequestTimeoutMiddleware, timeout_seconds=1)

    @app.get("/slow")
    async def slow():
        await asyncio.sleep(5)
        return {"ok": True}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/slow")

    assert resp.status_code == 503
    data = resp.json()
    assert data["success"] is False
    assert data["error"]["code"] == "REQUEST_TIMEOUT"
    assert "timed out after" in data["error"]["message"]


@pytest.mark.asyncio
async def test_timeout_middleware_uses_configured_timeout():
    from fastapi import FastAPI
    from app.middleware.timeout import RequestTimeoutMiddleware

    app = FastAPI()
    app.add_middleware(RequestTimeoutMiddleware, timeout_seconds=2)

    @app.get("/check")
    async def check():
        return {"timeout": 2}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/check")

    assert resp.status_code == 200
    assert "timed out after" not in resp.text


@pytest.mark.asyncio
async def test_timeout_middleware_integrated_in_app():
    from app.main import create_app

    app = create_app()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/health")

    assert resp.status_code == 200
