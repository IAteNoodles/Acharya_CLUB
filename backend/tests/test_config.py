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
                                                    "HOST", "PORT", "DATABASE_URL",
                                                    "JWT_SECRET", "JWT_ALGORITHM", "JWT_ACCESS_EXPIRE_MINUTES",
                                                    "JWT_REFRESH_EXPIRE_DAYS", "CORS_ORIGINS", "LOG_LEVEL"))]
    for k in keys:
        del os.environ[k]
    yield
    _restore_core_modules(saved)


def test_config_loads_with_env_vars():
    os.environ["ENVIRONMENT"] = "test"
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./acharya_club.db"
    os.environ["JWT_SECRET"] = "a" * 32
    os.environ["CORS_ORIGINS"] = '["http://localhost:3000"]'

    _reload_config()
    from app.core.config import get_settings
    settings = get_settings()

    assert settings.ENVIRONMENT == "test"
    assert settings.DATABASE_URL == "sqlite+aiosqlite:///./acharya_club.db"
    assert settings.JWT_SECRET == "a" * 32
    assert settings.CORS_ORIGINS == ["http://localhost:3000"]
    assert settings.PORT == 8000


def test_config_defaults():
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./acharya_club.db"
    os.environ["JWT_SECRET"] = "b" * 32

    _reload_config()
    from app.core.config import get_settings
    settings = get_settings()

    assert settings.ENVIRONMENT == "development"
    assert settings.PORT == 8000
    assert settings.LOG_LEVEL == "INFO"


def test_config_raises_on_missing_jwt_secret_in_production():
    os.environ["ENVIRONMENT"] = "production"
    os.environ["JWT_SECRET"] = ""
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./acharya_club.db"

    _reload_config()
    with pytest.raises(ValueError, match="JWT_SECRET must be set"):
        from app.core.config import Settings
        Settings()





def test_config_raises_on_placeholder_jwt_secret_in_production():
    for k in ["JWT_SECRET"]:
        if k in os.environ:
            del os.environ[k]

    os.environ["ENVIRONMENT"] = "production"
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./acharya_club.db"
    os.environ["JWT_SECRET"] = "change-this-to-a-random-string-at-least-32-chars"

    _reload_config()
    with pytest.raises(ValueError, match="JWT_SECRET must be set"):
        from app.core.config import Settings
        Settings()


def test_config_raises_on_short_jwt_secret():
    for k in ["DATABASE_URL", "JWT_SECRET"]:
        if k in os.environ:
            del os.environ[k]

    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./acharya_club.db"
    os.environ["JWT_SECRET"] = "short"

    _reload_config()
    with pytest.raises(ValueError, match="at least 32 characters"):
        from app.core.config import Settings
        Settings()
