from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
    verify_token,
)
from app.models.user import User, Role, UserStatus
from app.schemas.auth import SignupRequest

_blacklisted_tokens: set[str] = set()


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


async def refresh(refresh_token: str) -> dict:
    payload = verify_token(refresh_token)

    if payload.get("type") != "refresh":
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    if refresh_token in _blacklisted_tokens:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
        )

    user_id = payload["sub"]
    new_access = create_access_token(user_id=user_id, role="student")
    new_refresh = create_refresh_token(user_id=user_id)

    _blacklisted_tokens.add(refresh_token)

    return {"accessToken": new_access, "refreshToken": new_refresh}


async def logout(refresh_token: str) -> dict:
    _blacklisted_tokens.add(refresh_token)
    return {"message": "Logged out successfully"}


async def get_me(db: AsyncSession, user_id: str) -> dict:
    import uuid
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
