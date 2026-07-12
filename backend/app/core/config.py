import secrets
import warnings
from typing import List, Annotated
from urllib.parse import quote

from pydantic import model_validator, BeforeValidator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Application
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    APP_NAME: str = "Acharya_CLUB"
    API_PREFIX: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database — set DATABASE_URL or DB_PASSWORD in .env
    DATABASE_URL: str = "postgresql+asyncpg://postgres:localdev@localhost:5432/acharya"
    DB_USER: str = "postgres.qwouxrnnwmkotkwraqme"
    DB_PASSWORD: str = ""
    DB_HOST: str = "aws-1-ap-northeast-1.pooler.supabase.com"
    DB_PORT: int = 5432
    DB_NAME: str = "postgres"
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 3

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT — auto-generated random secret in development if not provided
    JWT_SECRET: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_EXPIRE_DAYS: int = 7

    # Security
    BCRYPT_ROUNDS: int = 12

    # Middleware
    REQUEST_TIMEOUT_SECONDS: int = 30

    # CORS
    CORS_ORIGINS: Annotated[List[str], BeforeValidator(lambda v: [i.strip() for i in v.split(",")] if isinstance(v, str) and not v.startswith("[") else v)] = ["http://localhost:5173", "http://localhost:8000"]

    # Logging
    LOG_LEVEL: str = "INFO"

    @model_validator(mode="after")
    def ensure_database_url(self):
        if not self.DATABASE_URL:
            if self.DB_PASSWORD:
                encoded = quote(self.DB_PASSWORD, safe="")
                self.DATABASE_URL = (
                    f"postgresql+asyncpg://{self.DB_USER}:{encoded}"
                    f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?ssl=require"
                )
            else:
                if self.ENVIRONMENT == "development":
                    warnings.warn(
                        "DATABASE_URL and DB_PASSWORD are not set. "
                        "App may fail to connect to database."
                    )
                else:
                    raise ValueError(
                        "Either DATABASE_URL must be set or DB_PASSWORD must be provided "
                        "as an environment variable"
                    )
        return self

    @model_validator(mode="after")
    def enforce_jwt_secret(self):
        if not self.JWT_SECRET or self.JWT_SECRET == "change-this-to-a-random-string-at-least-32-chars":
            if self.ENVIRONMENT == "development":
                self.JWT_SECRET = secrets.token_urlsafe(48)
                warnings.warn(
                    "JWT_SECRET not set — auto-generated a random development secret. "
                    "Tokens will be invalidated on restart."
                )
            else:
                raise ValueError(
                    "JWT_SECRET must be set in production. Generate one with:\n"
                    "  python -c \"import secrets; print(secrets.token_urlsafe(48))\""
                )
        elif len(self.JWT_SECRET) < 32:
            raise ValueError(
                f"JWT_SECRET must be at least 32 characters "
                f"(got {len(self.JWT_SECRET)})"
            )
        return self


settings = Settings()


def get_settings() -> Settings:
    return settings
