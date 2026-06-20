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
