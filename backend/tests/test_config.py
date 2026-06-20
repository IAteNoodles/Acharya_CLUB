import importlib
import os
import sys

import pytest


def _reload_config():
    for mod in list(sys.modules):
        if mod.startswith("app.core"):
            del sys.modules[mod]
    importlib.invalidate_caches()


def _save_core_modules():
    saved = {}
    for mod_name in list(sys.modules):
        if mod_name.startswith("app.core"):
            saved[mod_name] = sys.modules[mod_name]
    return saved


def _restore_core_modules(saved: dict):
    for mod_name in list(sys.modules):
        if mod_name.startswith("app.core"):
            del sys.modules[mod_name]
    sys.modules.update(saved)
    importlib.invalidate_caches()


@pytest.fixture(autouse=True)
def clear_env():
    saved = _save_core_modules()
    keys = [k for k in os.environ if k.startswith(("ENVIRONMENT", "DEBUG", "APP_NAME", "API_PREFIX",
                                                    "HOST", "PORT", "DATABASE_URL", "DATABASE_POOL_SIZE",
                                                    "DATABASE_MAX_OVERFLOW", "REDIS_URL", "JWT_SECRET",
                                                    "JWT_ALGORITHM", "JWT_ACCESS_EXPIRE_MINUTES",
                                                    "JWT_REFRESH_EXPIRE_DAYS", "CORS_ORIGINS", "LOG_LEVEL"))]
    for k in keys:
        del os.environ[k]
    yield
    _restore_core_modules(saved)


def test_config_loads_with_env_vars():
    os.environ["ENVIRONMENT"] = "test"
    os.environ["DATABASE_URL"] = "postgresql+asyncpg://test:test@localhost:5432/test"
    os.environ["JWT_SECRET"] = "a" * 32
    os.environ["CORS_ORIGINS"] = '["http://localhost:3000"]'

    _reload_config()
    from app.core.config import get_settings
    settings = get_settings()

    assert settings.ENVIRONMENT == "test"
    assert settings.DATABASE_URL == "postgresql+asyncpg://test:test@localhost:5432/test"
    assert settings.JWT_SECRET == "a" * 32
    assert settings.CORS_ORIGINS == ["http://localhost:3000"]
    assert settings.PORT == 8000


def test_config_defaults():
    os.environ["DATABASE_URL"] = "postgresql+asyncpg://u:p@localhost:5432/db"
    os.environ["JWT_SECRET"] = "b" * 32

    _reload_config()
    from app.core.config import get_settings
    settings = get_settings()

    assert settings.ENVIRONMENT == "development"
    assert settings.PORT == 8000
    assert settings.LOG_LEVEL == "INFO"


def test_config_raises_on_missing_required():
    # Temporarily remove .env so pydantic-settings can't read from it
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    renamed = False
    if os.path.exists(env_path):
        os.rename(env_path, env_path + ".bak")
        renamed = True

    try:
        for k in ["DATABASE_URL", "JWT_SECRET"]:
            if k in os.environ:
                del os.environ[k]

        _reload_config()
        with pytest.raises(Exception):
            from app.core.config import Settings
            Settings()
    finally:
        if renamed:
            os.rename(env_path + ".bak", env_path)
