import secrets
import warnings
from typing import List, Annotated

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

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./acharya_club.db"

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
