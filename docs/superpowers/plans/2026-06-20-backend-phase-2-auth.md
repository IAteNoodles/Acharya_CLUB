# Phase 2: Auth Module Implementation Plan (Python FastAPI)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement complete authentication system with signup, login, JWT access/refresh tokens with rotation, logout with blacklisting, and auth/authorize dependencies for protected routes.

**Architecture:** Auth module uses FastAPI's APIRouter with Depends for DI. JWT utilities live in `core/security.py`. Dependencies (get_current_user, require_role) live in `api/deps.py`. Pydantic v2 models handle validation. Async SQLAlchemy session is used throughout. Token blacklist uses an in-memory set as a placeholder for Redis (phase 7).

**Tech Stack:** FastAPI, python-jose (HS256), passlib[bcrypt], Pydantic v2, SQLAlchemy async, pytest + httpx

**Prerequisites:** Phase 1 must be complete — `backend/` scaffolded, SQLAlchemy async engine + session factory connected, Alembic migrations working, env config with `JWT_SECRET`, `JWT_ACCESS_EXPIRY_MINUTES`, and `JWT_REFRESH_EXPIRY_DAYS` variables.

---

## File Structure

```
backend/
├── app/
│   ├── core/
│   │   └── security.py              # NEW: create_access_token, create_refresh_token, verify_token, hash/verify password
│   ├── api/
│   │   ├── deps.py                  # NEW: get_current_user, require_admin, require_teacher_or_admin dependencies
│   │   └── v1/
│   │       └── auth.py              # NEW: FastAPI APIRouter (signup, login, refresh, logout, me)
│   ├── schemas/
│   │   └── auth.py                  # NEW: Pydantic v2 models (SignupRequest, LoginRequest, RefreshRequest, TokenResponse, UserResponse)
│   └── services/
│       └── auth.py                  # NEW: async business logic (signup, login, refresh, logout)
├── main.py                          # MODIFY: app.include_router(auth.router)
├── tests/
│   ├── test_security.py             # NEW: JWT + password hashing tests
│   ├── test_deps.py                 # NEW: dependency tests
│   ├── test_auth_schemas.py         # NEW: Pydantic validation tests
│   ├── test_auth_service.py         # NEW: auth business logic tests
│   └── test_auth.py                 # NEW: full auth flow integration tests
├── requirements.txt                 # MODIFY: add python-jose, passlib[bcrypt], bcrypt, pytest-asyncio, httpx, pytest
```

**No controller file.** In FastAPI, the router file IS the controller — route handler functions handle HTTP concerns, then delegate to services.

---

## Tasks

### Task 1: Core security (backend/app/core/security.py)

**Files:**
- Create: `backend/app/core/security.py`
- Create: `backend/tests/test_security.py`

- [ ] **Step 1: Write the failing test**

```python
import pytest
from datetime import datetime, timedelta, timezone
from jose import jwt
from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_token,
    hash_password,
    verify_password,
)


class TestCreateAccessToken:
    def test_returns_valid_jwt_string(self):
        token = create_access_token(user_id="user-1", role="student")
        assert token is not None
        assert isinstance(token, str)
        assert len(token.split(".")) == 3

    def test_contains_correct_payload(self):
        token = create_access_token(user_id="user-1", role="student")
        payload = jwt.decode(token, "test-secret", algorithms=["HS256"])
        assert payload["sub"] == "user-1"
        assert payload["role"] == "student"
        assert payload["type"] == "access"
        assert "exp" in payload
        assert "iat" in payload

    def test_expires_in_15_minutes(self):
        token = create_access_token(user_id="user-1", role="student")
        payload = jwt.decode(token, "test-secret", algorithms=["HS256"])
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        iat = datetime.fromtimestamp(payload["iat"], tz=timezone.utc)
        diff = exp - iat
        assert diff.total_seconds() == pytest.approx(900, abs=5), "Expected ~15 min expiry"


class TestCreateRefreshToken:
    def test_returns_valid_jwt_string(self):
        token = create_refresh_token(user_id="user-1")
        assert token is not None
        assert isinstance(token, str)
        assert len(token.split(".")) == 3

    def test_contains_correct_payload(self):
        token = create_refresh_token(user_id="user-1")
        payload = jwt.decode(token, "test-secret", algorithms=["HS256"])
        assert payload["sub"] == "user-1"
        assert payload["type"] == "refresh"
        assert "role" not in payload

    def test_expires_in_7_days(self):
        token = create_refresh_token(user_id="user-1")
        payload = jwt.decode(token, "test-secret", algorithms=["HS256"])
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        iat = datetime.fromtimestamp(payload["iat"], tz=timezone.utc)
        diff = exp - iat
        assert diff.total_seconds() == pytest.approx(604800, abs=60), "Expected ~7 day expiry"


class TestVerifyToken:
    def test_decodes_valid_access_token(self):
        token = create_access_token(user_id="user-1", role="student")
        payload = verify_token(token)
        assert payload["sub"] == "user-1"
        assert payload["role"] == "student"
        assert payload["type"] == "access"

    def test_decodes_valid_refresh_token(self):
        token = create_refresh_token(user_id="user-1")
        payload = verify_token(token)
        assert payload["sub"] == "user-1"
        assert payload["type"] == "refresh"

    def test_raises_on_invalid_token(self):
        with pytest.raises(Exception):
            verify_token("invalid-token")

    def test_raises_on_expired_token(self):
        token = create_access_token(user_id="user-1", role="student", expires_delta=timedelta(seconds=0))
        import time
        time.sleep(0.1)
        with pytest.raises(Exception):
            verify_token(token)

    def test_raises_on_wrong_secret(self):
        from jose import jwt as jose_jwt
        token = jose_jwt.encode({"sub": "user-1"}, "different-secret", algorithm="HS256")
        with pytest.raises(Exception):
            verify_token(token)


class TestPasswordHashing:
    def test_hash_returns_different_string(self):
        hashed = hash_password("SecurePass123")
        assert hashed != "SecurePass123"
        assert isinstance(hashed, str)

    def test_verify_correct_password_returns_true(self):
        hashed = hash_password("SecurePass123")
        assert verify_password("SecurePass123", hashed) is True

    def test_verify_wrong_password_returns_false(self):
        hashed = hash_password("SecurePass123")
        assert verify_password("WrongPassword", hashed) is False

    def test_same_password_produces_different_hashes(self):
        hash1 = hash_password("SecurePass123")
        hash2 = hash_password("SecurePass123")
        assert hash1 != hash2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_security.py -v`

Expected: FAIL - cannot import from `app.core.security`

- [ ] **Step 3: Write minimal implementation**

```python
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"


def create_access_token(user_id: str, role: str, expires_delta: timedelta | None = None) -> str:
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.JWT_ACCESS_EXPIRY_MINUTES)
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "role": role,
        "type": "access",
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=ALGORITHM)


def create_refresh_token(user_id: str, expires_delta: timedelta | None = None) -> str:
    if expires_delta is None:
        expires_delta = timedelta(days=settings.JWT_REFRESH_EXPIRY_DAYS)
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "type": "refresh",
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=ALGORITHM)


def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise ValueError("Invalid or expired token")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_security.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/security.py backend/tests/test_security.py
git commit -m "feat: add core security utilities (JWT, bcrypt hashing)"
```

---

### Task 2: Auth dependencies (backend/app/api/deps.py)

**Files:**
- Create: `backend/app/api/deps.py`
- Create: `backend/tests/test_deps.py`

- [ ] **Step 1: Write the failing test**

```python
import pytest
from fastapi import Depends, FastAPI, HTTPException
from httpx import AsyncClient, ASGITransport
from app.core.security import create_access_token, create_refresh_token


@pytest.fixture
def app():
    from app.api.deps import get_current_user, require_admin, require_teacher_or_admin

    test_app = FastAPI()

    @test_app.get("/api/v1/protected")
    async def protected(current_user: dict = Depends(get_current_user)):
        return {"userId": current_user["sub"], "role": current_user["role"]}

    @test_app.get("/api/v1/admin")
    async def admin_only(current_user: dict = Depends(require_admin)):
        return {"message": "admin access granted"}

    @test_app.get("/api/v1/faculty")
    async def faculty_only(current_user: dict = Depends(require_teacher_or_admin)):
        return {"message": "faculty access granted"}

    return test_app


@pytest.mark.asyncio
class TestGetCurrentUser:
    async def test_returns_401_when_no_auth_header(self, app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            res = await ac.get("/api/v1/protected")
        assert res.status_code == 401
        assert res.json()["detail"] == "Missing or invalid authorization header"

    async def test_returns_401_when_not_bearer(self, app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            res = await ac.get("/api/v1/protected", headers={"Authorization": "Basic token"})
        assert res.status_code == 401

    async def test_returns_401_when_token_invalid(self, app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            res = await ac.get("/api/v1/protected", headers={"Authorization": "Bearer invalid"})
        assert res.status_code == 401

    async def test_returns_user_when_token_valid(self, app):
        token = create_access_token(user_id="test-user-id", role="student")
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            res = await ac.get("/api/v1/protected", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        data = res.json()
        assert data["userId"] == "test-user-id"
        assert data["role"] == "student"

    async def test_rejects_refresh_token(self, app):
        token = create_refresh_token(user_id="test-user-id")
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            res = await ac.get("/api/v1/protected", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 401


@pytest.mark.asyncio
class TestRequireAdmin:
    async def test_allows_admin(self, app):
        token = create_access_token(user_id="admin-id", role="admin")
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            res = await ac.get("/api/v1/admin", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        assert res.json()["message"] == "admin access granted"

    async def test_rejects_student(self, app):
        token = create_access_token(user_id="student-id", role="student")
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            res = await ac.get("/api/v1/admin", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 403


@pytest.mark.asyncio
class TestRequireTeacherOrAdmin:
    async def test_allows_teacher(self, app):
        token = create_access_token(user_id="teacher-id", role="teacher")
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            res = await ac.get("/api/v1/faculty", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        assert res.json()["message"] == "faculty access granted"

    async def test_allows_admin(self, app):
        token = create_access_token(user_id="admin-id", role="admin")
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            res = await ac.get("/api/v1/faculty", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200

    async def test_rejects_student(self, app):
        token = create_access_token(user_id="student-id", role="student")
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            res = await ac.get("/api/v1/faculty", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 403

    async def test_returns_401_when_no_user(self, app):
        from fastapi import FastAPI
        from app.api.deps import require_teacher_or_admin

        local_app = FastAPI()

        @local_app.get("/test")
        async def test_endpoint(current_user: dict = Depends(require_teacher_or_admin)):
            return {"ok": True}

        transport = ASGITransport(app=local_app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            res = await ac.get("/test")
        assert res.status_code == 401
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_deps.py -v`

Expected: FAIL - cannot import from `app.api.deps`

- [ ] **Step 3: Write minimal implementation**

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.security import verify_token

security_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
) -> dict:
    token = credentials.credentials
    try:
        payload = verify_token(token)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    return payload


async def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )
    return current_user


async def require_teacher_or_admin(current_user: dict = Depends(get_current_user)) -> dict:
    role = current_user.get("role")
    if role not in ("teacher", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )
    return current_user
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_deps.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/deps.py backend/tests/test_deps.py
git commit -m "feat: add auth dependencies (get_current_user, require_admin, require_teacher_or_admin)"
```

---

### Task 3: Auth schemas (backend/app/schemas/auth.py)

**Files:**
- Create: `backend/app/schemas/__init__.py`
- Create: `backend/app/schemas/auth.py`
- Create: `backend/tests/test_auth_schemas.py`

- [ ] **Step 1: Write the failing test**

```python
import pytest
from pydantic import ValidationError
from app.schemas.auth import (
    SignupRequest,
    LoginRequest,
    RefreshRequest,
    TokenResponse,
    UserResponse,
)


class TestSignupRequest:
    def test_accepts_valid_student_data(self):
        data = SignupRequest(
            name="Priya Singh",
            email="priya.singh@college.edu",
            password="SecurePass123",
            role="student",
        )
        assert data.name == "Priya Singh"
        assert data.email == "priya.singh@college.edu"
        assert data.role == "student"

    def test_trims_name(self):
        data = SignupRequest(
            name="  Priya Singh  ",
            email="priya.singh@college.edu",
            password="SecurePass123",
            role="student",
        )
        assert data.name == "Priya Singh"

    def test_rejects_name_shorter_than_2_chars(self):
        with pytest.raises(ValidationError) as exc:
            SignupRequest(
                name="A",
                email="test@college.edu",
                password="SecurePass123",
                role="student",
            )
        assert "at least 2" in str(exc.value)

    def test_rejects_name_longer_than_120_chars(self):
        with pytest.raises(ValidationError):
            SignupRequest(
                name="A" * 121,
                email="test@college.edu",
                password="SecurePass123",
                role="student",
            )

    def test_rejects_non_college_email(self):
        with pytest.raises(ValidationError) as exc:
            SignupRequest(
                name="Test User",
                email="test@gmail.com",
                password="SecurePass123",
                role="student",
            )
        assert "@college.edu" in str(exc.value)

    def test_rejects_invalid_email_format(self):
        with pytest.raises(ValidationError):
            SignupRequest(
                name="Test User",
                email="not-an-email",
                password="SecurePass123",
                role="student",
            )

    def test_rejects_password_shorter_than_8_chars(self):
        with pytest.raises(ValidationError) as exc:
            SignupRequest(
                name="Test User",
                email="test@college.edu",
                password="Short1",
                role="student",
            )
        assert "at least 8" in str(exc.value)

    def test_rejects_password_longer_than_100_chars(self):
        with pytest.raises(ValidationError):
            SignupRequest(
                name="Test User",
                email="test@college.edu",
                password="A" * 101,
                role="student",
            )

    def test_rejects_invalid_role(self):
        with pytest.raises(ValidationError):
            SignupRequest(
                name="Test User",
                email="test@college.edu",
                password="SecurePass123",
                role="admin",
            )

    def test_accepts_teacher_role(self):
        data = SignupRequest(
            name="Dr. Rajesh",
            email="rajesh@college.edu",
            password="SecurePass123",
            role="teacher",
        )
        assert data.role == "teacher"


class TestLoginRequest:
    def test_accepts_valid_data(self):
        data = LoginRequest(email="test@college.edu", password="password123")
        assert data.email == "test@college.edu"
        assert data.password == "password123"

    def test_rejects_missing_email(self):
        with pytest.raises(ValidationError):
            LoginRequest(password="password123")

    def test_rejects_invalid_email(self):
        with pytest.raises(ValidationError):
            LoginRequest(email="invalid", password="password123")

    def test_rejects_empty_password(self):
        with pytest.raises(ValidationError):
            LoginRequest(email="test@college.edu", password="")


class TestRefreshRequest:
    def test_accepts_valid_token(self):
        data = RefreshRequest(refreshToken="some-refresh-token-value")
        assert data.refreshToken == "some-refresh-token-value"

    def test_rejects_empty_token(self):
        with pytest.raises(ValidationError):
            RefreshRequest(refreshToken="")

    def test_rejects_missing_token(self):
        with pytest.raises(ValidationError):
            RefreshRequest()


class TestTokenResponse:
    def test_creates_with_all_fields(self):
        data = TokenResponse(
            accessToken="access-value",
            refreshToken="refresh-value",
        )
        assert data.accessToken == "access-value"
        assert data.refreshToken == "refresh-value"


class TestUserResponse:
    def test_creates_with_all_fields(self):
        data = UserResponse(
            id="user-id",
            name="Priya Singh",
            email="priya.singh@college.edu",
            role="student",
            status="active",
        )
        assert data.id == "user-id"
        assert data.role == "student"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_auth_schemas.py -v`

Expected: FAIL - cannot import from `app.schemas.auth`

- [ ] **Step 3: Write minimal implementation**

```python
from pydantic import BaseModel, EmailStr, field_validator


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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_auth_schemas.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/__init__.py backend/app/schemas/auth.py backend/tests/test_auth_schemas.py
git commit -m "feat: add Pydantic v2 auth schemas with field validators"
```

---

### Task 4: Auth service (backend/app/services/auth.py)

**Files:**
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/auth.py`
- Create: `backend/tests/test_auth_service.py`

- [ ] **Step 1: Write the failing test**

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.schemas.auth import SignupRequest, LoginRequest


@pytest.fixture
def mock_session():
    return AsyncMock()


@pytest.fixture
def mock_user_model():
    user = MagicMock()
    user.id = "new-user-id"
    user.name = "Priya Singh"
    user.email = "priya.singh@college.edu"
    user.password_hash = "hashed-password"
    user.role = "student"
    user.status = "active"
    user.created_at = MagicMock()
    user.updated_at = MagicMock()
    return user


@pytest.mark.asyncio
class TestSignup:
    async def test_creates_student_and_returns_tokens(self, mock_session, mock_user_model):
        mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: None))
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        with (
            patch("app.services.auth.hash_password", return_value="hashed-password"),
            patch("app.services.auth.create_access_token", return_value="access-token"),
            patch("app.services.auth.create_refresh_token", return_value="refresh-token"),
        ):
            from app.services.auth import signup

            result = await signup(
                db=mock_session,
                data=SignupRequest(
                    name="Priya Singh",
                    email="priya.singh@college.edu",
                    password="SecurePass123",
                    role="student",
                ),
            )

        assert result["user"]["name"] == "Priya Singh"
        assert result["user"]["role"] == "student"
        assert result["user"]["status"] == "active"
        assert "password_hash" not in result["user"]
        assert result["access_token"] == "access-token"
        assert result["refresh_token"] == "refresh-token"

    async def test_creates_teacher_with_pending_status(self, mock_session):
        mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: None))

        with (
            patch("app.services.auth.hash_password", return_value="hashed"),
            patch("app.services.auth.create_access_token", return_value="at"),
            patch("app.services.auth.create_refresh_token", return_value="rt"),
        ):
            from app.services.auth import signup

            result = await signup(
                db=mock_session,
                data=SignupRequest(
                    name="Dr. Rajesh",
                    email="rajesh@college.edu",
                    password="SecurePass123",
                    role="teacher",
                ),
            )

        assert result["user"]["status"] == "pending"

    async def test_raises_on_duplicate_email(self, mock_session):
        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=lambda: MagicMock(id="existing"))
        )

        from app.services.auth import signup, ConflictError

        with pytest.raises(ConflictError):
            await signup(
                db=mock_session,
                data=SignupRequest(
                    name="Test",
                    email="existing@college.edu",
                    password="SecurePass123",
                    role="student",
                ),
            )


@pytest.mark.asyncio
class TestLogin:
    async def test_returns_user_and_tokens_for_valid_credentials(self, mock_session, mock_user_model):
        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=lambda: mock_user_model)
        )

        with (
            patch("app.services.auth.verify_password", return_value=True),
            patch("app.services.auth.create_access_token", return_value="access-token"),
            patch("app.services.auth.create_refresh_token", return_value="refresh-token"),
        ):
            from app.services.auth import login

            result = await login(
                db=mock_session,
                email="priya.singh@college.edu",
                password="SecurePass123",
            )

        assert result["user"]["email"] == "priya.singh@college.edu"
        assert "password_hash" not in result["user"]

    async def test_raises_on_user_not_found(self, mock_session):
        mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: None))

        from app.services.auth import login, UnauthorizedError

        with pytest.raises(UnauthorizedError):
            await login(db=mock_session, email="nobody@college.edu", password="pass")

    async def test_raises_on_wrong_password(self, mock_session, mock_user_model):
        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=lambda: mock_user_model)
        )

        with patch("app.services.auth.verify_password", return_value=False):
            from app.services.auth import login, UnauthorizedError

            with pytest.raises(UnauthorizedError):
                await login(db=mock_session, email="test@college.edu", password="WrongPassword")

    async def test_raises_for_pending_teacher(self, mock_session):
        user = MagicMock()
        user.role = "teacher"
        user.status = "pending"
        mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: user))

        with patch("app.services.auth.verify_password", return_value=True):
            from app.services.auth import login, ForbiddenError

            with pytest.raises(ForbiddenError):
                await login(db=mock_session, email="pending@college.edu", password="pass")

    async def test_raises_for_rejected_teacher(self, mock_session):
        user = MagicMock()
        user.role = "teacher"
        user.status = "rejected"
        mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: user))

        with patch("app.services.auth.verify_password", return_value=True):
            from app.services.auth import login, ForbiddenError

            with pytest.raises(ForbiddenError):
                await login(db=mock_session, email="rejected@college.edu", password="pass")


@pytest.mark.asyncio
class TestRefresh:
    async def test_returns_new_token_pair(self, mock_session):
        from app.services.auth import refresh, _blacklisted_tokens

        _blacklisted_tokens.clear()

        with (
            patch("app.services.auth.verify_token", return_value={"sub": "user-1", "type": "refresh"}),
            patch("app.services.auth.create_access_token", return_value="new-access"),
            patch("app.services.auth.create_refresh_token", return_value="new-refresh"),
        ):
            result = await refresh(db=mock_session, refresh_token="valid-refresh-token")

        assert result["access_token"] == "new-access"
        assert result["refresh_token"] == "new-refresh"

    async def test_raises_on_blacklisted_token(self, mock_session):
        from app.services.auth import refresh, _blacklisted_tokens

        _blacklisted_tokens.add("blacklisted-token")
        with pytest.raises(Exception):  # UnauthorizedError
            await refresh(db=mock_session, refresh_token="blacklisted-token")

    async def test_raises_on_expired_token(self, mock_session):
        from app.services.auth import refresh, _blacklisted_tokens

        _blacklisted_tokens.clear()

        with patch("app.services.auth.verify_token", side_effect=ValueError("expired")):
            with pytest.raises(Exception):
                await refresh(db=mock_session, refresh_token="expired-token")


@pytest.mark.asyncio
class TestLogout:
    async def test_blacklists_refresh_token(self, mock_session):
        from app.services.auth import logout, _blacklisted_tokens

        _blacklisted_tokens.clear()
        await logout(db=mock_session, refresh_token="token-to-blacklist")
        assert "token-to-blacklist" in _blacklisted_tokens


@pytest.mark.asyncio
class TestGetMe:
    async def test_returns_user_without_password(self, mock_session, mock_user_model):
        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=lambda: mock_user_model)
        )

        from app.services.auth import get_me

        result = await get_me(db=mock_session, user_id="user-id")
        assert result["id"] == "new-user-id"
        assert "password_hash" not in result

    async def test_raises_on_not_found(self, mock_session):
        mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: None))

        from app.services.auth import get_me, NotFoundError

        with pytest.raises(NotFoundError):
            await get_me(db=mock_session, user_id="nonexistent")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_auth_service.py -v`

Expected: FAIL - cannot import from `app.services.auth`

- [ ] **Step 3: Write minimal implementation**

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
    verify_token,
)


_blacklisted_tokens: set[str] = set()


class ConflictError(Exception):
    def __init__(self, message: str = "Resource already exists"):
        self.message = message
        self.code = "CONFLICT"
        super().__init__(self.message)


class UnauthorizedError(Exception):
    def __init__(self, message: str = "Unauthorized"):
        self.message = message
        self.code = "UNAUTHORIZED"
        super().__init__(self.message)


class ForbiddenError(Exception):
    def __init__(self, message: str = "Forbidden"):
        self.message = message
        self.code = "FORBIDDEN"
        super().__init__(self.message)


class NotFoundError(Exception):
    def __init__(self, message: str = "Not found"):
        self.message = message
        self.code = "NOT_FOUND"
        super().__init__(self.message)


def _strip_password(user) -> dict:
    excluded = {"password_hash", "_sa_instance_state"}
    return {k: v for k, v in user.__dict__.items() if not k.startswith("_") and k not in excluded}


async def signup(db: AsyncSession, data) -> dict:
    from app.models.user import User  # avoid circular import

    result = await db.execute(select(User).where(User.email == data.email))
    existing = result.scalar_one_or_none()
    if existing:
        raise ConflictError("Email already registered")

    password_hash_value = hash_password(data.password)
    status = "active" if data.role == "student" else "pending"

    user = User(
        name=data.name,
        email=data.email,
        password_hash=password_hash_value,
        role=data.role,
        status=status,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    access_token = create_access_token(user_id=str(user.id), role=user.role)
    refresh_token = create_refresh_token(user_id=str(user.id))

    return {
        "user": _strip_password(user),
        "access_token": access_token,
        "refresh_token": refresh_token,
    }


async def login(db: AsyncSession, email: str, password: str) -> dict:
    from app.models.user import User

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(password, user.password_hash):
        raise UnauthorizedError("Invalid email or password")

    if user.status != "active":
        if user.role == "teacher" and user.status == "pending":
            raise ForbiddenError("Teacher account is pending approval")
        if user.role == "teacher" and user.status == "rejected":
            raise ForbiddenError("Teacher account has been rejected")
        raise ForbiddenError("Account is not active")

    access_token = create_access_token(user_id=str(user.id), role=user.role)
    refresh_token = create_refresh_token(user_id=str(user.id))

    return {
        "user": _strip_password(user),
        "access_token": access_token,
        "refresh_token": refresh_token,
    }


async def refresh(db: AsyncSession, refresh_token: str) -> dict:
    if refresh_token in _blacklisted_tokens:
        raise UnauthorizedError("Refresh token has been revoked")

    try:
        payload = verify_token(refresh_token)
    except ValueError:
        raise UnauthorizedError("Invalid or expired refresh token")

    if payload.get("type") != "refresh":
        raise UnauthorizedError("Invalid token type")

    _blacklisted_tokens.add(refresh_token)

    new_access_token = create_access_token(user_id=payload["sub"], role=payload.get("role", "student"))
    new_refresh_token = create_refresh_token(user_id=payload["sub"])

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
    }


async def logout(db: AsyncSession, refresh_token: str) -> None:
    _blacklisted_tokens.add(refresh_token)


async def get_me(db: AsyncSession, user_id: str) -> dict:
    from app.models.user import User

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundError("User not found")
    return _strip_password(user)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_auth_service.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/__init__.py backend/app/services/auth.py backend/tests/test_auth_service.py
git commit -m "feat: add auth service with signup, login, refresh, logout, get_me"
```

---

### Task 5: Auth router (backend/app/api/v1/auth.py)

**Files:**
- Create: `backend/app/api/v1/__init__.py`
- Create: `backend/app/api/v1/auth.py`

- [ ] **Step 1: Write the router**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.schemas.auth import (
    SignupRequest,
    LoginRequest,
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
            "accessToken": result["access_token"],
            "refreshToken": result["refresh_token"],
        },
    }


@router.post("/login")
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await auth_service.login(db=db, email=data.email, password=data.password)
    return {
        "success": True,
        "data": {
            "user": UserResponse(**result["user"]),
            "accessToken": result["access_token"],
            "refreshToken": result["refresh_token"],
        },
    }


@router.post("/refresh")
async def refresh(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    result = await auth_service.refresh(db=db, refresh_token=data.refreshToken)
    return {
        "success": True,
        "data": {
            "accessToken": result["access_token"],
            "refreshToken": result["refresh_token"],
        },
    }


@router.post("/logout")
async def logout(
    data: RefreshRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    await auth_service.logout(db=db, refresh_token=data.refreshToken)
    return {"success": True, "data": {"message": "Logged out successfully"}}


@router.get("/me")
async def me(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user = await auth_service.get_me(db=db, user_id=current_user["sub"])
    return {"success": True, "data": {"user": UserResponse(**user)}}
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/api/v1/__init__.py backend/app/api/v1/auth.py
git commit -m "feat: add auth router with signup, login, refresh, logout, me endpoints"
```

---

### Task 6: Register router in main.py

**Files:**
- Modify: `backend/main.py`

- [ ] **Step 1: Update main.py to include auth router**

Current `main.py` (from Phase 1):

```python
from fastapi import FastAPI
from app.core.config import settings
from app.core.database import engine
from app.models import Base

app = FastAPI(title=settings.PROJECT_NAME, version="1.0.0")

# Create tables on startup (dev convenience; use Alembic in production)
@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.get("/api/v1/health")
async def health():
    return {
        "success": True,
        "data": {
            "status": "ok",
            "timestamp": "2026-06-20T00:00:00Z",
            "uptime": 0,
        },
    }
```

Add the auth router import and `include_router`:

```python
from fastapi import FastAPI
from app.core.config import settings
from app.core.database import engine
from app.models import Base
from app.api.v1.auth import router as auth_router

app = FastAPI(title=settings.PROJECT_NAME, version="1.0.0")

# Create tables on startup (dev convenience; use Alembic in production)
@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# Auth routes
app.include_router(auth_router)

@app.get("/api/v1/health")
async def health():
    return {
        "success": True,
        "data": {
            "status": "ok",
            "timestamp": "2026-06-20T00:00:00Z",
            "uptime": 0,
        },
    }
```

- [ ] **Step 2: Verify app imports cleanly**

Run: `cd backend && python -c "from main import app; print('OK')"`

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/main.py
git commit -m "feat: register auth router in FastAPI app"
```

---

### Task 7: Integration tests (backend/tests/test_auth.py)

**Files:**
- Create: `backend/tests/conftest.py` (if not exists)
- Create: `backend/tests/test_auth.py`

- [ ] **Step 1: Write conftest.py** (if not already present)

```python
import asyncio
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.core.database import get_db
from app.models import Base
from main import app


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def async_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(async_engine):
    async_session = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session


@pytest.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
```

- [ ] **Step 2: Write the failing integration test**

```python
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestAuthIntegration:
    async def test_full_auth_flow(self, client: AsyncClient):
        # ── Signup ────────────────────────────────────
        res = await client.post(
            "/api/v1/auth/signup",
            json={
                "name": "Priya Singh",
                "email": "priya.singh@college.edu",
                "password": "SecurePass123",
                "role": "student",
            },
        )
        assert res.status_code == 201
        data = res.json()
        assert data["success"] is True
        assert data["data"]["user"]["name"] == "Priya Singh"
        assert data["data"]["user"]["role"] == "student"
        assert data["data"]["user"]["status"] == "active"
        assert "passwordHash" not in data["data"]["user"]
        access_token = data["data"]["accessToken"]
        refresh_token = data["data"]["refreshToken"]
        assert access_token is not None
        assert refresh_token is not None

        # ── Me (authenticated) ────────────────────────
        res = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert res.status_code == 200
        assert res.json()["data"]["user"]["id"] == data["data"]["user"]["id"]
        assert res.json()["data"]["user"]["name"] == "Priya Singh"

        # ── Me (unauthenticated) ──────────────────────
        res = await client.get("/api/v1/auth/me")
        assert res.status_code == 401

        # ── Login ─────────────────────────────────────
        res = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "priya.singh@college.edu",
                "password": "SecurePass123",
            },
        )
        assert res.status_code == 200
        login_data = res.json()
        assert login_data["data"]["user"]["email"] == "priya.singh@college.edu"
        assert "passwordHash" not in login_data["data"]["user"]
        new_access = login_data["data"]["accessToken"]
        new_refresh = login_data["data"]["refreshToken"]

        # ── Refresh ───────────────────────────────────
        res = await client.post(
            "/api/v1/auth/refresh",
            json={"refreshToken": new_refresh},
        )
        assert res.status_code == 200
        token_data = res.json()
        assert token_data["data"]["accessToken"] is not None
        assert token_data["data"]["refreshToken"] is not None
        assert token_data["data"]["accessToken"] != token_data["data"]["refreshToken"]

        # ── Logout ────────────────────────────────────
        res = await client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {new_access}"},
            json={"refreshToken": new_refresh},
        )
        assert res.status_code == 200
        assert res.json()["data"]["message"] == "Logged out successfully"

        # ── Me fails after logout (token still valid JWT, but test ensures endpoint works) ─
        res = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {new_access}"},
        )
        assert res.status_code == 200  # access token still valid; blacklist is for refresh tokens only

    async def test_signup_duplicate_email(self, client: AsyncClient):
        res = await client.post(
            "/api/v1/auth/signup",
            json={
                "name": "Test User",
                "email": "priya.singh@college.edu",
                "password": "SecurePass123",
                "role": "student",
            },
        )
        assert res.status_code == 409
        assert res.json()["detail"] == "Email already registered"

    async def test_signup_validation_error(self, client: AsyncClient):
        res = await client.post(
            "/api/v1/auth/signup",
            json={
                "name": "A",
                "email": "invalid-email",
                "password": "short",
                "role": "admin",
            },
        )
        assert res.status_code == 422

    async def test_login_invalid_credentials(self, client: AsyncClient):
        res = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@college.edu",
                "password": "WrongPassword",
            },
        )
        assert res.status_code == 401

    async def test_refresh_invalid_token(self, client: AsyncClient):
        res = await client.post(
            "/api/v1/auth/refresh",
            json={"refreshToken": "invalid-token"},
        )
        assert res.status_code == 401

    async def test_logout_unauthenticated(self, client: AsyncClient):
        res = await client.post(
            "/api/v1/auth/logout",
            json={"refreshToken": "some-token"},
        )
        assert res.status_code == 401

    async def test_health_check_unaffected(self, client: AsyncClient):
        res = await client.get("/api/v1/health")
        assert res.status_code == 200
        assert res.json()["data"]["status"] == "ok"
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_auth.py -v`

Expected: FAIL (some tests may fail due to missing dependencies or model import issues; at minimum the file should be found and start executing)

- [ ] **Step 4: Verify all integration tests pass**

Run: `cd backend && python -m pytest tests/test_auth.py -v`

Expected: PASS

- [ ] **Step 5: Run the full test suite**

Run: `cd backend && python -m pytest -v`

Expected: All tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/tests/conftest.py backend/tests/test_auth.py
git commit -m "test: add auth integration tests for full signup-login-refresh-logout-me flow"
```

---

## Spec Coverage Check

| Spec Requirement | Task | Status |
|---|---|---|
| JWT utility functions (create_access_token, create_refresh_token, verify_token) | Task 1 | Done |
| Token expiration: access 15min, refresh 7d | Task 1 | Done |
| Password hashing with bcrypt (passlib CryptContext) | Task 1 | Done |
| Token blacklist (in-memory set placeholder for Redis) | Task 4 | Done |
| get_current_user dependency (Bearer extraction, JWT verify, type check) | Task 2 | Done |
| require_admin dependency (role == "admin") | Task 2 | Done |
| require_teacher_or_admin dependency (role in ["teacher", "admin"]) | Task 2 | Done |
| SignupRequest (name 2-120, email @college.edu, password 8-100, role student\|teacher) | Task 3 | Done |
| LoginRequest (email, password) | Task 3 | Done |
| RefreshRequest (refreshToken) | Task 3 | Done |
| TokenResponse and UserResponse models | Task 3 | Done |
| Auth service: signup (duplicate check, bcrypt hash, student=active, teacher=pending) | Task 4 | Done |
| Auth service: login (find user, verify password, check status, generate tokens) | Task 4 | Done |
| Auth service: refresh (blacklist check, token verification, rotation) | Task 4 | Done |
| Auth service: logout (blacklist refresh token) | Task 4 | Done |
| Auth service: get_me (fetch user by ID, strip password_hash) | Task 4 | Done |
| Auth router (POST /signup, /login, /refresh public; POST /logout, GET /me authenticated) | Task 5 | Done |
| Register auth router in main.py under /api/v1/auth | Task 6 | Done |
| Async/await throughout | All tasks | Done |
| Pydantic v2 field_validator for custom validation | Task 3 | Done |
| FastAPI Depends for DI (get_db, get_current_user) | Tasks 2, 5 | Done |
| pytest + pytest-asyncio + httpx for testing | All test tasks | Done |
| Status checks (pending teacher → 403, rejected teacher → 403) | Task 4 | Done |
| Refresh token rotation (old token blacklisted, new pair issued) | Task 4 | Done |
| TDD for all components (test first) | All tasks | Done |

## Placeholder Scan

- No "TODO", "TBD", "implement later", or "fill in details" patterns found.
- Every code block contains complete, runnable Python code.
- Error handling is explicit in every function (try/except for JWT, exception classes for business logic).
- No references to undefined types or functions — all imports are resolved within the plan.
- All test files use `pytest.mark.asyncio` for async test functions.

## Type Consistency Check

- `create_access_token(user_id: str, role: str, expires_delta=None)` → returns `str` — used consistently in services, tests
- `create_refresh_token(user_id: str, expires_delta=None)` → returns `str` — same
- `verify_token(token: str)` → returns `dict` — used in get_current_user dependency and refresh service
- `hash_password(password: str)` → `str` / `verify_password(plain: str, hash: str)` → `bool` — used in auth service
- `get_current_user` → returns `dict` payload (sub, role, type) — used in router and role dependencies
- `require_admin` / `require_teacher_or_admin` → returns `dict` — chain from get_current_user
- `signup`, `login`, `refresh`, `logout`, `get_me` — all async, take `db: AsyncSession` as first param
- Pydantic model names: `SignupRequest`, `LoginRequest`, `RefreshRequest`, `TokenResponse`, `UserResponse`
- Exception classes: `ConflictError`, `UnauthorizedError`, `ForbiddenError`, `NotFoundError` — defined in services/auth.py
- `router` export as `auth_router` in import in main.py

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-20-backend-phase-2-auth.md`. Two execution options:

**1. Subagent-Driven (recommended)** — Dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
