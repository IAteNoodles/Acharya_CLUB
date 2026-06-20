from pydantic import BaseModel, field_validator


class SignupRequest(BaseModel):
    name: str
    email: str
    password: str
    role: str = "student"

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Name must be at least 2 characters")
        if len(v) > 120:
            raise ValueError("Name must not exceed 120 characters")
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Invalid email format")
        if not v.endswith("@college.edu"):
            raise ValueError("Must use a @college.edu email address")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if len(v) > 100:
            raise ValueError("Password must not exceed 100 characters")
        return v

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in ("student", "teacher"):
            raise ValueError('Role must be "student" or "teacher"')
        return v


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Invalid email format")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not v:
            raise ValueError("Password is required")
        return v


class RefreshRequest(BaseModel):
    refreshToken: str

    @field_validator("refreshToken")
    @classmethod
    def validate_refresh_token(cls, v: str) -> str:
        if not v:
            raise ValueError("Refresh token is required")
        return v


class TokenResponse(BaseModel):
    accessToken: str
    refreshToken: str


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    role: str
    status: str
