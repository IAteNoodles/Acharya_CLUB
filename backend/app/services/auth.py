import uuid
from datetime import timedelta

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.redis import get_redis
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
    verify_token,
)
from app.models.user import User, Role, UserStatus
from app.schemas.auth import SignupRequest

logger = structlog.get_logger()

_blacklisted_tokens_fallback: set[str] = set()

_BLACKLIST_PREFIX = "bl:"


async def _is_blacklisted(token: str) -> bool:
    redis = await get_redis()
    if redis is not None:
        try:
            exists = await redis.get(_BLACKLIST_PREFIX + token)
            return exists is not None
        except Exception:
            logger.warning("Redis check failed, falling back to in-memory blacklist")
    return token in _blacklisted_tokens_fallback


async def _add_to_blacklist(token: str, ttl_seconds: int) -> None:
    redis = await get_redis()
    if redis is not None:
        try:
            await redis.setex(_BLACKLIST_PREFIX + token, ttl_seconds, "1")
            return
        except Exception:
            logger.warning("Redis set failed, falling back to in-memory blacklist")
    _blacklisted_tokens_fallback.add(token)


def _enum_val(v):
    return v.value if hasattr(v, 'value') else v


async def signup(db: AsyncSession, data: SignupRequest) -> dict:
    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none():
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )

    user = User(
        name=data.name.strip(),
        email=data.email,
        password_hash=hash_password(data.password),
        role=Role.STUDENT if data.role == "student" else Role.TEACHER,
        status=UserStatus.ACTIVE if data.role == "student" else UserStatus.PENDING,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    access_token = create_access_token(user_id=str(user.id), role=_enum_val(user.role))
    refresh_token = create_refresh_token(user_id=str(user.id))

    return {
        "user": {
            "id": str(user.id),
            "name": user.name,
            "email": user.email,
            "role": _enum_val(user.role),
            "status": _enum_val(user.status),
        },
        "accessToken": access_token,
        "refreshToken": refresh_token,
    }


async def login(db: AsyncSession, email: str, password: str) -> dict:
    from fastapi import HTTPException, status

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if _enum_val(user.status) != UserStatus.ACTIVE.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is not active. Please contact administrator.",
        )

    access_token = create_access_token(user_id=str(user.id), role=_enum_val(user.role))
    refresh_token = create_refresh_token(user_id=str(user.id))

    return {
        "user": {
            "id": str(user.id),
            "name": user.name,
            "email": user.email,
            "role": _enum_val(user.role),
            "status": _enum_val(user.status),
        },
        "accessToken": access_token,
        "refreshToken": refresh_token,
    }


async def refresh(db: AsyncSession, refresh_token: str) -> dict:
    from fastapi import HTTPException, status

    try:
        payload = verify_token(refresh_token)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    if payload.get("type") != "refresh":
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    if await _is_blacklisted(refresh_token):
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
        )

    user_id = payload["sub"]
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    actual_role = _enum_val(user.role)

    new_access = create_access_token(user_id=user_id, role=actual_role)
    new_refresh = create_refresh_token(user_id=user_id)

    await _add_to_blacklist(refresh_token, settings.JWT_REFRESH_EXPIRE_DAYS * 86400)

    return {"accessToken": new_access, "refreshToken": new_refresh}


async def logout(refresh_token: str) -> dict:
    await _add_to_blacklist(refresh_token, settings.JWT_REFRESH_EXPIRE_DAYS * 86400)
    return {"message": "Logged out successfully"}


async def get_me(db: AsyncSession, user_id: str) -> dict:
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()

    if not user:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return {
        "id": str(user.id),
        "name": user.name,
        "email": user.email,
        "role": _enum_val(user.role),
        "status": _enum_val(user.status),
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None,
    }
