import pytest
from httpx import AsyncClient, ASGITransport


@pytest.mark.asyncio
async def test_create_app_returns_fastapi_instance(app):
    assert app is not None
    assert app.title == "Acharya_CLUB"


@pytest.mark.asyncio
async def test_app_has_cors_middleware(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.options(
            "/api/v1/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"


@pytest.mark.asyncio
async def test_app_has_docs_enabled_in_debug(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/docs")
    assert response.status_code == 200
