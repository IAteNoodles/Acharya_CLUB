import uuid
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from app.api.v1.auth import router as auth_router
from app.api.v1.events import router as events_router
from app.api.v1.health import router as health_router
from app.api.v1.registrations import router as registrations_router
from app.api.v1.users import router as users_router
from app.core.config import get_settings
from app.core.database import engine
from app.core.exceptions import register_exception_handlers
from app.core.logging_config import setup_logging
from app.core.redis import get_redis, close_redis
from app.middleware.security import SecurityHeadersMiddleware

settings = get_settings()
logger = setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up application")

    redis = await get_redis()
    if redis:
        logger.info("Redis client initialized")
    else:
        logger.warning("Redis not configured — rate limiter will use in-memory fallback")

    try:
        async with engine.connect() as conn:
            await conn.run_sync(lambda sync_conn: None)
    except Exception:
        pass

    yield

    logger.info("Shutting down application")
    await close_redis()
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
    for path in openapi_schema["paths"].values():
        for method in path.values():
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

    register_exception_handlers(app)

    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        request_id = str(uuid.uuid4())
        with structlog.contextvars.bound_contextvars(request_id=request_id):
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response

    app.include_router(health_router, prefix=settings.API_PREFIX, tags=["health"])
    app.include_router(auth_router)
    app.include_router(events_router)
    app.include_router(registrations_router)
    app.include_router(users_router)

    return app
