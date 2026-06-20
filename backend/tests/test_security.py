import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_security_headers_present():
    from fastapi import FastAPI
    from app.middleware.security import SecurityHeadersMiddleware

    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/test")
    async def test_endpoint():
        return {"ok": True}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/test")

    assert resp.headers.get("x-content-type-options") == "nosniff"
    assert resp.headers.get("x-frame-options") == "DENY"
    assert resp.headers.get("x-xss-protection") == "1; mode=block"
    assert resp.headers.get("strict-transport-security") is not None
    assert resp.headers.get("referrer-policy") is not None
