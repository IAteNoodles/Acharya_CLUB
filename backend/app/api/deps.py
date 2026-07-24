from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.core.security import verify_token
from app.services.auth import _is_blacklisted

security_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
) -> dict:
    if credentials is None:
        raise UnauthorizedException(detail="Not authenticated")
    token = credentials.credentials

    if await _is_blacklisted(token):
        raise UnauthorizedException(detail="Token has been revoked")

    try:
        payload = verify_token(token)
    except ValueError:
        raise UnauthorizedException(detail="Invalid or expired token")

    if payload.get("type") != "access":
        raise UnauthorizedException(detail="Invalid token type")

    return payload


async def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user.get("role") != "admin":
        raise ForbiddenException("Insufficient permissions")
    return current_user


async def require_teacher_or_admin(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user is None:
        raise UnauthorizedException(detail="Not authenticated")
    role = current_user.get("role")
    if role not in ("teacher", "admin"):
        raise ForbiddenException("Insufficient permissions")
    return current_user


async def require_student(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user.get("role") != "student":
        raise ForbiddenException("Only students can perform this action")
    return current_user
