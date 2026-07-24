from typing import Any, Dict, List, Optional
from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppHTTPException(Exception):
    def __init__(
        self,
        status_code: int,
        detail: str = "An error occurred",
        error_code: str = "INTERNAL_ERROR",
        headers: Optional[Dict[str, str]] = None,
    ):
        self.status_code = status_code
        self.detail = detail
        self.error_code = error_code
        self.headers = headers
        super().__init__(detail)


class NotFoundException(AppHTTPException):
    def __init__(self, resource: str = "Resource", detail: Optional[str] = None):
        super().__init__(
            status_code=404,
            detail=detail or f"{resource} not found",
            error_code="NOT_FOUND",
        )


class UnauthorizedException(AppHTTPException):
    def __init__(self, detail: str = "Authentication required"):
        super().__init__(
            status_code=401,
            detail=detail,
            error_code="UNAUTHORIZED",
            headers={"WWW-Authenticate": "Bearer"},
        )


class ForbiddenException(AppHTTPException):
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(
            status_code=403,
            detail=detail,
            error_code="FORBIDDEN",
        )


class ValidationException(AppHTTPException):
    def __init__(
        self,
        errors: List[Dict[str, Any]],
        detail: str = "Validation failed",
    ):
        self.errors = errors
        super().__init__(
            status_code=422,
            detail=detail,
            error_code="VALIDATION_ERROR",
        )


class ConflictException(AppHTTPException):
    def __init__(self, detail: str = "Resource already exists"):
        super().__init__(
            status_code=409,
            detail=detail,
            error_code="CONFLICT",
        )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppHTTPException)
    async def app_http_exception_handler(request: Request, exc: AppHTTPException):
        body: Dict[str, Any] = {
            "success": False,
            "error": {
                "code": exc.error_code,
                "message": exc.detail,
            },
        }
        if isinstance(exc, ValidationException):
            body["error"]["details"] = exc.errors
        return JSONResponse(
            status_code=exc.status_code,
            content=body,
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Validation failed",
                    "details": jsonable_encoder(exc.errors()),
                },
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def starlette_http_exception_handler(request: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": "NOT_FOUND" if exc.status_code == 404 else "HTTP_ERROR",
                    "message": exc.detail,
                },
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Internal server error",
                },
            },
        )
