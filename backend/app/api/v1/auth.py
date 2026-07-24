from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.schemas.auth import (
    SignupRequest,
    LoginRequest,
    ChangePasswordRequest,
    RefreshRequest,
    TokenResponse,
    UserResponse,
)
from app.services import auth as auth_service
from app.core.database import get_db

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/signup", status_code=201)
async def signup(data: SignupRequest, db: AsyncSession = Depends(get_db)):
    result = await auth_service.signup(db=db, data=data)
    return {
        "success": True,
        "data": {
            "user": UserResponse(**result["user"]),
            "accessToken": result["accessToken"],
            "refreshToken": result["refreshToken"],
        },
    }


@router.post("/login")
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await auth_service.login(db=db, email=data.email, password=data.password)
    return {
        "success": True,
        "data": {
            "user": UserResponse(**result["user"]),
            "accessToken": result["accessToken"],
            "refreshToken": result["refreshToken"],
        },
    }


@router.post("/refresh")
async def refresh(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    result = await auth_service.refresh(db=db, refresh_token=data.refreshToken)
    return {
        "success": True,
        "data": {
            "accessToken": result["accessToken"],
            "refreshToken": result["refreshToken"],
        },
    }


@router.post("/logout")
async def logout(
    data: RefreshRequest,
    current_user: dict = Depends(get_current_user),
):
    await auth_service.logout(refresh_token=data.refreshToken)
    return {"success": True, "data": {"message": "Logged out successfully"}}


@router.post("/change-password")
async def change_password(
    data: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = await auth_service.change_password(
        db=db,
        user_id=current_user["sub"],
        current_password=data.currentPassword,
        new_password=data.newPassword,
    )
    return {"success": True, "data": result}


@router.get("/me")
async def me(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user = await auth_service.get_me(db=db, user_id=current_user["sub"])
    return {"success": True, "data": {"user": UserResponse(**user)}}
