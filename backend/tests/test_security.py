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


def test_hash_password_returns_string():
    from app.core.security import hash_password

    hashed = hash_password("SecurePass123")
    assert isinstance(hashed, str)
    assert len(hashed) > 20
    assert hashed != "SecurePass123"


def test_hash_password_produces_different_hashes():
    from app.core.security import hash_password

    h1 = hash_password("SecurePass123")
    h2 = hash_password("SecurePass123")
    assert h1 != h2


def test_verify_password_correct():
    from app.core.security import hash_password, verify_password

    hashed = hash_password("SecurePass123")
    assert verify_password("SecurePass123", hashed) is True


def test_verify_password_incorrect():
    from app.core.security import hash_password, verify_password

    hashed = hash_password("SecurePass123")
    assert verify_password("WrongPassword", hashed) is False
