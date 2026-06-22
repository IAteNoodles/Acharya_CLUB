import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.core.exceptions import (
    AppHTTPException,
    NotFoundException,
    UnauthorizedException,
    ForbiddenException,
    ValidationException,
    ConflictException,
    register_exception_handlers,
)


def test_app_http_exception():
    exc = AppHTTPException(status_code=400, detail="Bad request", error_code="BAD_REQUEST")
    assert exc.status_code == 400
    assert exc.detail == "Bad request"
    assert exc.error_code == "BAD_REQUEST"


def test_not_found_exception():
    exc = NotFoundException(resource="User")
    assert exc.status_code == 404
    assert "User" in exc.detail


def test_unauthorized_exception():
    exc = UnauthorizedException()
    assert exc.status_code == 401
    assert exc.error_code == "UNAUTHORIZED"


def test_forbidden_exception():
    exc = ForbiddenException()
    assert exc.status_code == 403
    assert exc.error_code == "FORBIDDEN"


def test_validation_exception():
    exc = ValidationException(errors=[{"field": "email", "message": "Invalid format"}])
    assert exc.status_code == 422
    assert exc.error_code == "VALIDATION_ERROR"
    assert len(exc.errors) == 1


def test_conflict_exception():
    exc = ConflictException(detail="Email already exists")
    assert exc.status_code == 409
    assert exc.error_code == "CONFLICT"


def test_exception_handlers_register():
    app = FastAPI()
    register_exception_handlers(app)
    assert len(app.exception_handlers) > 0


def test_validation_exception_handler_includes_errors():
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/test")
    async def test_route():
        raise ValidationException(
            errors=[{"loc": ["email"], "msg": "Invalid format"}],
            detail="Validation failed",
        )

    from fastapi.testclient import TestClient
    client = TestClient(app)
    resp = client.get("/test")

    assert resp.status_code == 422
    data = resp.json()
    assert data["success"] is False
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert "details" in data["error"]
    assert data["error"]["details"] == [{"loc": ["email"], "msg": "Invalid format"}]


def test_unhandled_exception_handler():
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/panic")
    async def panic():
        raise RuntimeError("something went terribly wrong")

    from fastapi.testclient import TestClient
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/panic")

    assert resp.status_code == 500
    data = resp.json()
    assert data["success"] is False
    assert data["error"]["code"] == "INTERNAL_ERROR"
    assert "Internal server error" in data["error"]["message"]
