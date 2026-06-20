from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.auth import router as auth_router
from app.api.v1.events import router as events_router
from app.api.v1.health import router as health_router
from app.api.v1.registrations import router as registrations_router
from app.api.v1.users import router as users_router
from app.core.config import get_settings
from app.core.database import engine
from app.core.exceptions import register_exception_handlers

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        async with engine.connect() as conn:
            await conn.run_sync(lambda sync_conn: None)
    except Exception:
        pass
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    app.include_router(health_router, prefix=settings.API_PREFIX, tags=["health"])
    app.include_router(auth_router)
    app.include_router(events_router)
    app.include_router(registrations_router)
    app.include_router(users_router)

    return app
