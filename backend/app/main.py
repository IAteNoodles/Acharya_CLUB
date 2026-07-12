import uuid
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from app.api.v1.attendance import router as attendance_router
from app.api.v1.auth import router as auth_router
from app.api.v1.events import router as events_router
from app.api.v1.health import router as health_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.registrations import router as registrations_router
from app.api.v1.reports import router as reports_router
from app.api.v1.users import router as users_router
from app.core.config import get_settings
from app.core.database import engine
from app.core.exceptions import register_exception_handlers
from app.core.logging_config import setup_logging
from app.models.base import Base
from app.middleware.security import SecurityHeadersMiddleware
from app.middleware.timeout import RequestTimeoutMiddleware

settings = get_settings()
logger = setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up application")

    try:
        async with engine.connect() as conn:
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database schema created successfully (if it didn't exist)")
    except Exception as exc:
        logger.warning("Database connection/schema check failed at startup", error=str(exc))

    yield

    logger.info("Shutting down application")
    await engine.dispose()
    logger.info("Graceful shutdown complete")


def custom_openapi(app: FastAPI):
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=settings.APP_NAME,
        version="1.0.0",
        description="College Event Management System — REST API built with FastAPI",
        routes=app.routes,
        contact={"name": "Acharya_CLUB Team", "email": "team@acharyaclub.edu"},
    )
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    public_prefixes = ("/api/v1/health", "/api/v1/docs", "/api/v1/redoc", "/api/v1/openapi.json")
    for path, methods in openapi_schema["paths"].items():
        if path.startswith(public_prefixes):
            continue
        for method in methods.values():
            if "security" not in method:
                method["security"] = []
            method["security"].append({"BearerAuth": []})
    app.openapi_schema = openapi_schema
    return app.openapi_schema


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/api/v1/docs",
        redoc_url="/api/v1/redoc",
        openapi_url="/api/v1/openapi.json",
        openapi_tags=[
            {"name": "health", "description": "Health check endpoints"},
            {"name": "Auth", "description": "Authentication and authorization"},
            {"name": "Users", "description": "User management"},
            {"name": "Events", "description": "Event management"},
            {"name": "Registrations", "description": "Event registrations"},
            {"name": "Attendance", "description": "Attendance tracking"},
            {"name": "notifications", "description": "In-app notifications"},
            {"name": "reports", "description": "Reports and dashboard"},
        ],
    )

    app.openapi = lambda: custom_openapi(app)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestTimeoutMiddleware, timeout_seconds=settings.REQUEST_TIMEOUT_SECONDS)

    register_exception_handlers(app)



    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        request_id = str(uuid.uuid4())
        with structlog.contextvars.bound_contextvars(request_id=request_id):
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response

    app.include_router(health_router, prefix=settings.API_PREFIX, tags=["health"])
    app.include_router(auth_router, prefix=settings.API_PREFIX + "/auth")
    app.include_router(events_router, prefix=settings.API_PREFIX + "/events")
    app.include_router(registrations_router, prefix=settings.API_PREFIX + "/registrations")
    app.include_router(attendance_router, prefix=settings.API_PREFIX + "/attendance")
    app.include_router(notifications_router, prefix=settings.API_PREFIX + "/notifications")
    app.include_router(reports_router, prefix=settings.API_PREFIX + "/reports")
    app.include_router(users_router, prefix=settings.API_PREFIX + "/users")

    return app


app = create_app()
