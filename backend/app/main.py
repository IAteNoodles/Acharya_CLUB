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
from app.core.redis import get_redis, close_redis
from app.middleware.security import SecurityHeadersMiddleware
from app.middleware.timeout import RequestTimeoutMiddleware

settings = get_settings()
logger = setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up application")

    redis = await get_redis()
    if redis:
        logger.info("Redis client initialized — rate limiter will use Redis backend")
    else:
        logger.warning("Redis not configured — rate limiter will use in-memory fallback")

    from app.middleware.rate_limit import get_rate_limiter
    rate_limit_check = await get_rate_limiter(
        max_requests=100,
        window_seconds=60,
    )
    rate_limit_auth_check = await get_rate_limiter(
        max_requests=20,
        window_seconds=60,
    )
    app.state.rate_limit_check = rate_limit_check
    app.state.rate_limit_auth_check = rate_limit_auth_check
    logger.info("Rate limiter initialized (general: 100/min, auth: 20/min)")

    try:
        async with engine.connect() as conn:
            await conn.run_sync(lambda sync_conn: None)
    except Exception as exc:
        logger.warning("Database connection check failed at startup", error=str(exc))

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
    async def rate_limit_middleware(request: Request, call_next):
        path = request.url.path
        is_auth = path.startswith(settings.API_PREFIX + "/auth")
        rate_limit_check = getattr(
            request.app.state,
            "rate_limit_auth_check" if is_auth else "rate_limit_check",
            None,
        )
        if rate_limit_check and not path.startswith(settings.API_PREFIX + "/health"):
            try:
                await rate_limit_check(request)
            except HTTPException as exc:
                return JSONResponse(
                    status_code=exc.status_code,
                    content={
                        "success": False,
                        "error": {
                            "code": "RATE_LIMITED",
                            "message": exc.detail,
                        },
                    },
                    headers=getattr(exc, "headers", None),
                )
        return await call_next(request)

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
    app.include_router(attendance_router)
    app.include_router(notifications_router)
    app.include_router(reports_router)
    app.include_router(users_router)

    return app


app = create_app()
