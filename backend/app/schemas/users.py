import uuid
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from typing import Optional


class UserOut(BaseModel):
    id: str
    name: str
    email: str
    role: str
    status: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_validator("id", mode="before")
    @classmethod
    def validate_uuid(cls, v):
        if isinstance(v, uuid.UUID):
            v = str(v)
        uuid.UUID(v)
        return v

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        allowed = {"student", "teacher", "admin"}
        if v not in allowed:
            raise ValueError(f"Role must be one of {allowed}")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        allowed = {"pending", "active", "rejected"}
        if v not in allowed:
            raise ValueError(f"Status must be one of {allowed}")
        return v

    model_config = {"from_attributes": True}


class PendingTeachersResponse(BaseModel):
    success: bool = True
    users: list[UserOut]
    total: int
    page: int
    limit: int
    total_pages: int


class TeacherListResponse(BaseModel):
    success: bool = True
    users: list[UserOut]
    total: int
    page: int
    limit: int
    total_pages: int


class UserActionResponse(BaseModel):
    success: bool = True
    data: UserOut
