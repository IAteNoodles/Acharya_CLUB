# Acharya_CLUB — API Specification

> College Event Management System  
> Base URL: `/api/v1`  
> Protocol: HTTPS (production) / HTTP (development)  
> Content-Type: `application/json`  
> Authentication: Bearer JWT (`Authorization: Bearer <token>`)

---

## 1. Response Format

### 1.1 Success Response

```python
from pydantic import BaseModel
from typing import Generic, TypeVar, Optional
from datetime import datetime

T = TypeVar("T")


# Single resource
class SuccessResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T


# Paginated list
class PaginatedData(BaseModel, Generic[T]):
    data: list[T]
    meta: "PaginationMeta"


class PaginationMeta(BaseModel):
    page: int
    limit: int
    total: int
    totalPages: int


# Mutation with message
class MessageResponse(BaseModel):
    success: bool = True
    data: "MessageData"


class MessageData(BaseModel):
    message: str
```

### 1.2 Error Response

```python
class ErrorDetail(BaseModel):
    code: str                              # Machine-readable error code
    message: str                           # Human-readable description
    details: Optional[list["FieldError"]] = None  # Present for validation errors


class FieldError(BaseModel):
    field: str
    message: str


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail
```

---

## 2. HTTP Status Code Conventions

| Status Code | Meaning | When |
|---|---|---|
| `200 OK` | Success | GET, PATCH, POST (non-creation), DELETE |
| `201 Created` | Resource created | POST (signup, create event, register) |
| `400 Bad Request` | Validation error | Invalid input, missing fields |
| `401 Unauthorized` | Not authenticated | Missing/invalid/expired token |
| `403 Forbidden` | Insufficient permissions | Wrong role, not resource owner |
| `404 Not Found` | Resource not found | Invalid ID, deleted resource |
| `409 Conflict` | Duplicate or state conflict | Already registered, duplicate email |
| `429 Too Many Requests` | Rate limited | Too many requests in window |
| `500 Internal Server Error` | Server error | Unhandled exception |

Usage in FastAPI:

```python
from fastapi import status

@router.post("/events", status_code=status.HTTP_201_CREATED)
@router.get("/events", status_code=status.HTTP_200_OK)
```

---

## 3. Authentication

All endpoints except `POST /auth/signup`, `POST /auth/login`, and `POST /auth/refresh` require the `Authorization` header:

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

**FastAPI dependency injection:**

```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.models.user import User

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    """Extract and validate JWT from Authorization header."""
    token = credentials.credentials
    # Validate token, return user or raise 401
    ...
```

**Usage in endpoints:**

```python
@router.get("/me", response_model=SuccessResponse[UserResponse])
async def get_me(
    current_user: User = Depends(get_current_user),
):
    """Get current user profile."""
    return current_user
```

**Token details:**

| Token | Lifetime | Storage | Rotation |
|---|---|---|---|
| Access Token | 15 minutes | Client (memory/localStorage) | Not rotated |
| Refresh Token | 7 days | Client (secure/httpOnly cookie or storage) | Rotated on each use; old token invalidated |

**Refresh token rotation breach detection:** If a rotated-out refresh token is ever reused, all refresh tokens for that user are revoked.

**Token blacklist:** On logout, the access token's `jti` is added to Redis with a TTL matching its remaining validity. Every authenticated request checks the blacklist.

---

## 4. Error Codes Reference

| Code | HTTP Status | Description |
|---|---|---|
| `VALIDATION_ERROR` | 400 | Input failed Pydantic schema validation. `details` array contains per-field errors. |
| `UNAUTHORIZED` | 401 | Missing `Authorization` header or token is malformed. |
| `TOKEN_EXPIRED` | 401 | Access token's `exp` claim is in the past. Client should refresh. |
| `TOKEN_BLACKLISTED` | 401 | Token was invalidated via logout. |
| `FORBIDDEN` | 403 | Authenticated user lacks the required role or is not the resource owner. |
| `EMAIL_NOT_VERIFIED` | 403 | Student account has not verified email address. |
| `TEACHER_PENDING` | 403 | Teacher account has not been approved by admin. |
| `NOT_FOUND` | 404 | No resource exists for the given ID. |
| `CONFLICT` | 409 | Duplicate entry (e.g., email already registered, already registered for event). |
| `EVENT_NOT_APPROVED` | 409 | Cannot register for an event that is not in `approved` status. |
| `EVENT_FULL` | 409 | Event has reached `maxRegistrations`. |
| `RATE_LIMITED` | 429 | Request quota exceeded for the current window. |
| `INTERNAL_ERROR` | 500 | Unexpected server error. Stack trace returned in development only. |

**Raising errors in FastAPI:**

```python
from fastapi import HTTPException
from app.core.exceptions import AppException

# Using custom exception handler
raise AppException(
    code="EVENT_FULL",
    status_code=status.HTTP_409_CONFLICT,
    message="Event has reached maximum registrations.",
)
```

---

## 5. Pagination

### 5.1 Query Parameters

| Param | Type | Default | Max | Description |
|---|---|---|---|---|
| `page` | `int` (query) | 1 | — | Page number (1-indexed) |
| `limit` | `int` (query) | 20 | 100 | Items per page |

### 5.2 FastAPI Query Model

```python
from fastapi import Query


class PaginationParams:
    """Dependency class for pagination query parameters."""

    def __init__(
        self,
        page: int = Query(1, ge=1, description="Page number"),
        limit: int = Query(20, ge=1, le=100, description="Items per page"),
    ):
        self.page = page
        self.limit = limit
```

### 5.3 Response Meta

```python
class PaginationMeta(BaseModel):
    page: int = 1
    limit: int = 20
    total: int = 156
    totalPages: int = 8
```

### 5.4 Example Request

```
GET /api/v1/events?page=2&limit=10&status=approved
```

### 5.5 Usage in Endpoint

```python
@router.get("/events", response_model=SuccessResponse[list[EventResponse]])
async def list_events(
    pagination: PaginationParams = Depends(),
    status: Optional[EventStatus] = Query(None),
    current_user: User = Depends(get_current_user),
):
    ...
```

---

## 6. Rate Limiting

| Scope | Limit | Backend |
|---|---|---|
| Authentication (login, signup) | 10 attempts / 15 min / IP | Redis sliding window |
| General API | 100 requests / 1 min / IP | Redis sliding window |
| Attendance marking | 30 requests / 1 min / user | Redis sliding window |

**Headers returned on every response:**

| Header | Description |
|---|---|
| `X-RateLimit-Limit` | Max requests allowed in the window |
| `X-RateLimit-Remaining` | Requests remaining in the current window |
| `X-RateLimit-Reset` | Unix timestamp when the window resets |

**On limit exceeded (429):**

```json
{
  "success": false,
  "error": {
    "code": "RATE_LIMITED",
    "message": "Too many requests. Please try again in 45 seconds."
  }
}
```

---

## 7. Module: Auth (`/api/v1/auth`)

```python
from fastapi import APIRouter, Depends, status
from app.schemas.auth import (
    SignupRequest, LoginRequest, RefreshRequest,
    LogoutRequest, TokenResponse, UserResponse,
)
from app.api.deps import get_current_user
from app.models.user import User
from app.services import auth_service

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
```

---

### 7.1 POST /auth/signup

Register a new student or teacher account.

**Authentication:** None  
**Rate limited:** Yes (10/15min per IP)

**Pydantic Schema:**

```python
from pydantic import BaseModel, field_validator
from enum import Enum


class RoleEnum(str, Enum):
    student = "student"
    teacher = "teacher"


class SignupRequest(BaseModel):
    name: str                                    # Min 2, max 120 characters
    email: str                                   # Must end with @college.edu
    password: str                                # Min 8, max 100 characters
    role: RoleEnum

    @field_validator("name")
    @classmethod
    def validate_name_length(cls, v: str) -> str:
        stripped = v.strip()
        if len(stripped) < 2 or len(stripped) > 120:
            raise ValueError("Name must be 2–120 characters")
        return stripped

    @field_validator("email")
    @classmethod
    def validate_college_email(cls, v: str) -> str:
        if not v.endswith("@college.edu"):
            raise ValueError("Must use a @college.edu email address")
        return v

    @field_validator("password")
    @classmethod
    def validate_password_length(cls, v: str) -> str:
        if len(v) < 8 or len(v) > 100:
            raise ValueError("Password must be 8–100 characters")
        return v
```

**Validation Rules:**

| Field | Rule |
|---|---|
| `name` | 2–120 characters, trimmed |
| `email` | Valid email format, must end with `@college.edu` |
| `password` | 8–100 characters |
| `role` | Must be `"student"` or `"teacher"` |

**Role-Specific Behavior:**

| Role | Initial Status | Result |
|---|---|---|
| `student` | `active` | Can immediately browse and register for events |
| `teacher` | `pending` | Must be approved by admin before accessing the system |

**Response `201 Created`:**

```json
{
  "success": true,
  "data": {
    "user": {
      "id": "uuid",
      "name": "Priya Singh",
      "email": "priya.singh@college.edu",
      "role": "student",
      "status": "active",
      "createdAt": "2026-06-20T10:00:00.000Z"
    },
    "accessToken": "eyJhbGciOiJIUzI1NiIs...",
    "refreshToken": "dGhpcyBpcyBhIHJlZnJlc2ggdG9rZW4..."
  }
}
```

**Endpoint:**

```python
@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(request: SignupRequest):
    """Register a new student or teacher account."""
    return await auth_service.signup(request)
```

**Error Responses:**

| Code | Scenario |
|---|---|
| `VALIDATION_ERROR` | Invalid name/email/password/role format |
| `CONFLICT` | Email already registered |

---

### 7.2 POST /auth/login

Authenticate with email and password.

**Authentication:** None  
**Rate limited:** Yes (10/15min per IP)

**Pydantic Schema:**

```python
class LoginRequest(BaseModel):
    email: str
    password: str
```

**Response `200 OK`:**

```json
{
  "success": true,
  "data": {
    "user": {
      "id": "uuid",
      "name": "Priya Singh",
      "email": "priya.singh@college.edu",
      "role": "student",
      "status": "active",
      "createdAt": "2026-06-20T10:00:00.000Z"
    },
    "accessToken": "eyJhbGciOiJIUzI1NiIs...",
    "refreshToken": "dGhpcyBpcyBhIHJlZnJlc2ggdG9rZW4..."
  }
}
```

**Endpoint:**

```python
@router.post("/login", response_model=SuccessResponse[TokenResponse])
async def login(request: LoginRequest):
    """Authenticate user and return JWT tokens."""
    return await auth_service.login(request.email, request.password)
```

**Error Responses:**

| Code | Scenario |
|---|---|
| `VALIDATION_ERROR` | Missing/invalid email or password |
| `UNAUTHORIZED` | Invalid email or password |
| `FORBIDDEN` | Teacher account is `pending` or `rejected` |

---

### 7.3 POST /auth/refresh

Obtain a new access token using a refresh token. Implements token rotation — the old refresh token is invalidated and a new one is issued.

**Authentication:** None

**Pydantic Schema:**

```python
class RefreshRequest(BaseModel):
    refreshToken: str
```

**Response `200 OK`:**

```json
{
  "success": true,
  "data": {
    "accessToken": "eyJhbGciOiJIUzI1NiIs...",
    "refreshToken": "bmV3IHJlZnJlc2ggdG9rZW4..."
  }
}
```

**Endpoint:**

```python
@router.post("/refresh", response_model=SuccessResponse[TokenResponse])
async def refresh(request: RefreshRequest):
    """Refresh access token using refresh token."""
    return await auth_service.refresh(request.refreshToken)
```

**Error Responses:**

| Code | Scenario |
|---|---|
| `VALIDATION_ERROR` | Missing refresh token |
| `UNAUTHORIZED` | Invalid or expired refresh token |
| `UNAUTHORIZED` | Refresh token reuse detected (breach) — all tokens revoked |

---

### 7.4 POST /auth/logout

Invalidate the current access token and refresh token.

**Authentication:** Required

**Pydantic Schema:**

```python
class LogoutRequest(BaseModel):
    refreshToken: Optional[str] = None  # Optional; if provided, also blacklisted
```

**Response `200 OK`:**

```json
{
  "success": true,
  "data": {
    "message": "Logged out successfully"
  }
}
```

**Endpoint:**

```python
@router.post("/logout", response_model=SuccessResponse[MessageData])
async def logout(
    request: LogoutRequest,
    current_user: User = Depends(get_current_user),
):
    """Logout and blacklist tokens."""
    return await auth_service.logout(current_user, request.refreshToken)
```

---

### 7.5 GET /auth/me

Get the currently authenticated user's full profile.

**Authentication:** Required

**Response `200 OK`:**

```json
{
  "success": true,
  "data": {
    "user": {
      "id": "uuid",
      "name": "Priya Singh",
      "email": "priya.singh@college.edu",
      "role": "student",
      "status": "active",
      "createdAt": "2026-06-20T10:00:00.000Z",
      "updatedAt": "2026-06-20T10:00:00.000Z"
    }
  }
}
```

**Endpoint:**

```python
@router.get("/me", response_model=SuccessResponse[UserResponse])
async def get_me(
    current_user: User = Depends(get_current_user),
):
    """Get current user's profile."""
    return current_user
```

---

## 8. Module: Users (`/api/v1/users`)

```python
router = APIRouter(prefix="/api/v1/users", tags=["users"])
```

### 8.1 GET /users/pending-teachers

List all teacher accounts with `status = pending`.

**Authentication:** Required  
**Authorization:** `admin` only

**FastAPI authorization dependency:**

```python
from app.api.deps import require_admin

@router.get("/pending-teachers", response_model=SuccessResponse[list[UserResponse]])
async def list_pending_teachers(
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(require_admin),
):
    """List all pending teacher accounts."""
    return await user_service.get_pending_teachers(pagination)
```

**Query Parameters:**

| Param | Type | Default | Description |
|---|---|---|---|
| `page` | `int` (query) | 1 | Page number |
| `limit` | `int` (query) | 20 | Items per page (max 100) |

**Response `200 OK`:**

```json
{
  "success": true,
  "data": [
    {
      "id": "uuid",
      "name": "Prof. Sunita Sharma",
      "email": "sunita.sharma@college.edu",
      "role": "teacher",
      "status": "pending",
      "createdAt": "2026-06-19T08:30:00.000Z"
    }
  ],
  "meta": {
    "page": 1,
    "limit": 20,
    "total": 1,
    "totalPages": 1
  }
}
```

---

### 8.2 PATCH /users/{id}/approve

Approve a pending teacher account. Sets `status` to `active`.

**Authentication:** Required  
**Authorization:** `admin` only

**Path Parameters:**

| Param | Type | Description |
|---|---|---|
| `id` | `uuid` (path) | User ID of the pending teacher |

**Endpoint:**

```python
@router.patch("/{id}/approve", response_model=SuccessResponse[UserResponse])
async def approve_teacher(
    id: str,
    current_user: User = Depends(require_admin),
):
    """Approve a pending teacher account."""
    return await user_service.approve_teacher(id)
```

**Response `200 OK`:**

```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "name": "Prof. Sunita Sharma",
    "email": "sunita.sharma@college.edu",
    "role": "teacher",
    "status": "active",
    "updatedAt": "2026-06-20T11:00:00.000Z"
  }
}
```

**Error Responses:**

| Code | Scenario |
|---|---|
| `NOT_FOUND` | User not found |
| `CONFLICT` | User is not a teacher or status is not `pending` |

---

### 8.3 PATCH /users/{id}/reject

Reject a pending teacher account. Sets `status` to `rejected`.

**Authentication:** Required  
**Authorization:** `admin` only

**Path Parameters:**

| Param | Type | Description |
|---|---|---|
| `id` | `uuid` (path) | User ID of the pending teacher |

**Endpoint:**

```python
@router.patch("/{id}/reject", response_model=SuccessResponse[UserResponse])
async def reject_teacher(
    id: str,
    current_user: User = Depends(require_admin),
):
    """Reject a pending teacher account."""
    return await user_service.reject_teacher(id)
```

**Response `200 OK`:**

```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "name": "Prof. Sunita Sharma",
    "email": "sunita.sharma@college.edu",
    "role": "teacher",
    "status": "rejected",
    "updatedAt": "2026-06-20T11:00:00.000Z"
  }
}
```

**Error Responses:**

| Code | Scenario |
|---|---|
| `NOT_FOUND` | User not found |
| `CONFLICT` | User is not a teacher or status is not `pending` |

---

### 8.4 GET /users/teachers

List all active teacher accounts.

**Authentication:** Required  
**Authorization:** `admin` only

**Query Parameters:**

| Param | Type | Default | Description |
|---|---|---|---|
| `page` | `int` (query) | 1 | Page number |
| `limit` | `int` (query) | 20 | Items per page (max 100) |
| `search` | `str` (query) | — | Optional search by name or email (case-insensitive partial match) |

**Endpoint:**

```python
@router.get("/teachers", response_model=SuccessResponse[list[UserResponse]])
async def list_teachers(
    pagination: PaginationParams = Depends(),
    search: Optional[str] = Query(None, max_length=200),
    current_user: User = Depends(require_admin),
):
    """List all active teachers."""
    return await user_service.get_teachers(pagination=pagination, search=search)
```

**Response `200 OK`:**

```json
{
  "success": true,
  "data": [
    {
      "id": "uuid",
      "name": "Dr. Rajesh Kumar",
      "email": "rajesh.kumar@college.edu",
      "role": "teacher",
      "status": "active",
      "createdAt": "2026-06-18T09:00:00.000Z"
    }
  ],
  "meta": {
    "page": 1,
    "limit": 20,
    "total": 1,
    "totalPages": 1
  }
}
```

---

## 9. Module: Events (`/api/v1/events`)

```python
router = APIRouter(prefix="/api/v1/events", tags=["events"])
```

### 9.1 GET /events

List events. Results are filtered based on the authenticated user's role.

**Authentication:** Required

**Role-Based Filtering:**

| Role | Visible Events |
|---|---|
| `student` | Events with `status = approved` |
| `teacher` | Events where `coordinatorId` matches the teacher (assigned events) |
| `admin` | All events regardless of status |

**Query Parameters:**

| Param | Type | Default | Description |
|---|---|---|---|
| `page` | `int` (query) | 1 | Page number |
| `limit` | `int` (query) | 20 | Items per page (max 100) |
| `status` | `EventStatus` (query) | — | Filter by status (`draft`, `pending`, `approved`, `rejected`) |
| `type` | `EventType` (query) | — | Filter by type (`in_college`, `out_college`) |
| `category` | `EventCategory` (query) | — | Filter by category (`volunteer`, `participant`, `both`) |
| `search` | `str` (query) | — | Search by title (case-insensitive partial match) |

**Pydantic Query Schema:**

```python
from fastapi import Query
from typing import Optional


class EventQueryParams:
    """Dependency for event listing query parameters."""

    def __init__(
        self,
        page: int = Query(1, ge=1),
        limit: int = Query(20, ge=1, le=100),
        status: Optional[EventStatus] = Query(None),
        type: Optional[EventType] = Query(None),
        category: Optional[EventCategory] = Query(None),
        search: Optional[str] = Query(None, max_length=200),
    ):
        self.page = page
        self.limit = limit
        self.status = status
        self.type = type
        self.category = category
        self.search = search
```

**Response `200 OK`:**

```json
{
  "success": true,
  "data": [
    {
      "id": "uuid",
      "title": "Annual Tech Fest 2026",
      "description": "A two-day technology festival...",
      "type": "in_college",
      "category": "both",
      "status": "approved",
      "venue": "Main Auditorium & CS Block",
      "startDate": "2026-07-04T00:00:00.000Z",
      "endDate": "2026-07-05T00:00:00.000Z",
      "maxRegistrations": 200,
      "registrationCount": 3,
      "createdBy": {
        "id": "uuid",
        "name": "System Administrator"
      },
      "coordinator": {
        "id": "uuid",
        "name": "Dr. Rajesh Kumar"
      },
      "createdAt": "2026-06-18T10:00:00.000Z"
    }
  ],
  "meta": {
    "page": 1,
    "limit": 20,
    "total": 4,
    "totalPages": 1
  }
}
```

**Endpoint:**

```python
@router.get("", response_model=SuccessResponse[list[EventResponse]])
async def list_events(
    query: EventQueryParams = Depends(),
    current_user: User = Depends(get_current_user),
):
    """List events (role-filtered)."""
    return await event_service.list_events(query, current_user)
```

---

### 9.2 POST /events

Create a new event.

**Authentication:** Required  
**Authorization:** `admin` creates `in_college` type; `student` creates `out_college` type. Teachers can create either type.

**Status Assignment on Creation:**

| Creator Role | Event Type | Initial Status |
|---|---|---|
| `student` | `out_college` | `pending` |
| `teacher` | `in_college` | `approved` (auto-approved) |
| `teacher` | `out_college` | `pending` |
| `admin` | `in_college` | `approved` |
| `admin` | `out_college` | `approved` |

**Pydantic Schema:**

```python
from datetime import datetime


class CreateEventRequest(BaseModel):
    title: str                              # Min 3, max 200 characters
    description: Optional[str] = None       # Max 2000 characters
    type: EventType
    category: EventCategory
    venue: str                              # Min 2, max 300 characters
    startDate: datetime                     # ISO 8601; must be in the future
    endDate: datetime                       # ISO 8601; must be after startDate
    maxRegistrations: int = 0               # Min 1, default 0 (unlimited)

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        stripped = v.strip()
        if len(stripped) < 3 or len(stripped) > 200:
            raise ValueError("Title must be 3–200 characters")
        return stripped

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        if v and len(v) > 2000:
            raise ValueError("Description must not exceed 2000 characters")
        return v

    @field_validator("venue")
    @classmethod
    def validate_venue(cls, v: str) -> str:
        stripped = v.strip()
        if len(stripped) < 2 or len(stripped) > 300:
            raise ValueError("Venue must be 2–300 characters")
        return stripped

    @field_validator("maxRegistrations")
    @classmethod
    def validate_max_registrations(cls, v: int) -> int:
        if v < 0:
            raise ValueError("maxRegistrations must be >= 0")
        return v

    @model_validator(mode="after")
    def validate_dates(self) -> "CreateEventRequest":
        if self.endDate <= self.startDate:
            raise ValueError("End date must be after start date")
        if self.startDate <= datetime.now(self.startDate.tzinfo):
            raise ValueError("Start date must be in the future")
        return self
```

**Response `201 Created`:**

```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "title": "Debate Competition: Current Affairs",
    "description": "Inter-department debate competition...",
    "type": "in_college",
    "category": "participant",
    "status": "pending",
    "venue": "Seminar Hall, 3rd Floor",
    "startDate": "2026-06-27T00:00:00.000Z",
    "endDate": "2026-06-28T00:00:00.000Z",
    "maxRegistrations": 32,
    "createdBy": "uuid",
    "coordinatorId": "uuid",
    "createdAt": "2026-06-20T12:00:00.000Z"
  }
}
```

**Endpoint:**

```python
@router.post("", status_code=status.HTTP_201_CREATED)
async def create_event(
    request: CreateEventRequest,
    current_user: User = Depends(get_current_user),
):
    """Create a new event."""
    return await event_service.create_event(request, current_user)
```

---

### 9.3 GET /events/{id}

Get detailed information about a specific event, including registration and attendance counts.

**Authentication:** Required

**Path Parameters:**

| Param | Type | Description |
|---|---|---|
| `id` | `uuid` (path) | Event ID |

**Response `200 OK`:**

```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "title": "Annual Tech Fest 2026",
    "description": "A two-day technology festival...",
    "type": "in_college",
    "category": "both",
    "status": "approved",
    "venue": "Main Auditorium & CS Block",
    "startDate": "2026-07-04T00:00:00.000Z",
    "endDate": "2026-07-05T00:00:00.000Z",
    "maxRegistrations": 200,
    "registrationCount": 3,
    "attendanceCount": 0,
    "createdBy": {
      "id": "uuid",
      "name": "System Administrator",
      "email": "admin@college.edu"
    },
    "coordinator": {
      "id": "uuid",
      "name": "Dr. Rajesh Kumar",
      "email": "rajesh.kumar@college.edu"
    },
    "createdAt": "2026-06-18T10:00:00.000Z",
    "updatedAt": "2026-06-18T10:00:00.000Z"
  }
}
```

**Endpoint:**

```python
@router.get("/{id}", response_model=SuccessResponse[EventDetailResponse])
async def get_event(
    id: str,
    current_user: User = Depends(get_current_user),
):
    """Get detailed event information."""
    return await event_service.get_event(id, current_user)
```

**Error Responses:**

| Code | Scenario |
|---|---|
| `NOT_FOUND` | Event not found |
| `FORBIDDEN` | Student trying to access non-approved event |

---

### 9.4 PATCH /events/{id}

Update event details. Only updatable while event status is `draft` or `pending`.

**Authentication:** Required  
**Authorization:** Event creator or `admin`

**Path Parameters:**

| Param | Type | Description |
|---|---|---|
| `id` | `uuid` (path) | Event ID |

**Pydantic Schema (all fields optional):**

```python
class UpdateEventRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    type: Optional[EventType] = None
    category: Optional[EventCategory] = None
    venue: Optional[str] = None
    startDate: Optional[datetime] = None
    endDate: Optional[datetime] = None
    maxRegistrations: Optional[int] = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            stripped = v.strip()
            if len(stripped) < 3 or len(stripped) > 200:
                raise ValueError("Title must be 3–200 characters")
            return stripped
        return v

    @field_validator("venue")
    @classmethod
    def validate_venue(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            stripped = v.strip()
            if len(stripped) < 2 or len(stripped) > 300:
                raise ValueError("Venue must be 2–300 characters")
            return stripped
        return v

    @field_validator("maxRegistrations")
    @classmethod
    def validate_max(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 0:
            raise ValueError("maxRegistrations must be >= 0")
        return v
```

**Response `200 OK`:**

```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "title": "Updated Event Title",
    "description": "Updated description...",
    "type": "in_college",
    "category": "volunteer",
    "status": "draft",
    "venue": "New Venue",
    "startDate": "2026-07-10T00:00:00.000Z",
    "endDate": "2026-07-11T00:00:00.000Z",
    "maxRegistrations": 50,
    "createdBy": "uuid",
    "coordinatorId": "uuid",
    "createdAt": "2026-06-18T10:00:00.000Z",
    "updatedAt": "2026-06-20T13:00:00.000Z"
  }
}
```

**Endpoint:**

```python
@router.patch("/{id}", response_model=SuccessResponse[EventResponse])
async def update_event(
    id: str,
    request: UpdateEventRequest,
    current_user: User = Depends(get_current_user),
):
    """Update event details."""
    return await event_service.update_event(id, request, current_user)
```

**Error Responses:**

| Code | Scenario |
|---|---|
| `NOT_FOUND` | Event not found |
| `FORBIDDEN` | User is not the creator or admin |
| `CONFLICT` | Event status does not allow updates (e.g., `approved`) |

---

### 9.5 PATCH /events/{id}/approve

Approve a pending event. Changes status from `pending` to `approved`.

**Authentication:** Required  
**Authorization:** `admin` or teacher assigned as event coordinator

**Path Parameters:**

| Param | Type | Description |
|---|---|---|
| `id` | `uuid` (path) | Event ID |

**Pydantic Schema:**

```python
class ApproveEventRequest(BaseModel):
    adminComment: Optional[str] = None  # Optional comment, max 500 characters
```

**Response `200 OK`:**

```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "title": "National Hackathon: CodeForCause",
    "status": "approved",
    "adminComment": "Approved. Ensure security arrangements are in place.",
    "updatedAt": "2026-06-20T14:00:00.000Z"
  }
}
```

**Endpoint:**

```python
@router.patch("/{id}/approve", response_model=SuccessResponse[EventApprovalResponse])
async def approve_event(
    id: str,
    request: ApproveEventRequest,
    current_user: User = Depends(get_current_user),
):
    """Approve a pending event."""
    return await event_service.approve_event(id, request, current_user)
```

**Error Responses:**

| Code | Scenario |
|---|---|
| `NOT_FOUND` | Event not found |
| `FORBIDDEN` | Teacher is not the assigned coordinator |
| `CONFLICT` | Event status is not `pending` |

---

### 9.6 PATCH /events/{id}/reject

Reject a pending event. Changes status from `pending` to `rejected`.

**Authentication:** Required  
**Authorization:** `admin` or teacher assigned as event coordinator

**Path Parameters:**

| Param | Type | Description |
|---|---|---|
| `id` | `uuid` (path) | Event ID |

**Pydantic Schema:**

```python
class RejectEventRequest(BaseModel):
    adminComment: str  # Required reason for rejection, max 1000 characters

    @field_validator("adminComment")
    @classmethod
    def validate_comment(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Rejection reason is required")
        if len(stripped) > 1000:
            raise ValueError("Comment must not exceed 1000 characters")
        return stripped
```

**Response `200 OK`:**

```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "title": "National Hackathon: CodeForCause",
    "status": "rejected",
    "adminComment": "Insufficient budget allocation. Please revise and resubmit.",
    "updatedAt": "2026-06-20T14:00:00.000Z"
  }
}
```

**Endpoint:**

```python
@router.patch("/{id}/reject", response_model=SuccessResponse[EventApprovalResponse])
async def reject_event(
    id: str,
    request: RejectEventRequest,
    current_user: User = Depends(get_current_user),
):
    """Reject a pending event."""
    return await event_service.reject_event(id, request, current_user)
```

**Error Responses:**

| Code | Scenario |
|---|---|
| `VALIDATION_ERROR` | Missing `adminComment` |
| `NOT_FOUND` | Event not found |
| `FORBIDDEN` | Teacher is not the assigned coordinator |
| `CONFLICT` | Event status is not `pending` |

---

### 9.7 PATCH /events/{id}/assign-coordinator

Assign or change the teacher coordinator for an event.

**Authentication:** Required  
**Authorization:** `admin` only

**Path Parameters:**

| Param | Type | Description |
|---|---|---|
| `id` | `uuid` (path) | Event ID |

**Pydantic Schema:**

```python
class AssignCoordinatorRequest(BaseModel):
    coordinatorId: str  # UUID of an active teacher
```

**Response `200 OK`:**

```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "title": "Annual Tech Fest 2026",
    "coordinatorId": "uuid",
    "coordinator": {
      "id": "uuid",
      "name": "Dr. Rajesh Kumar",
      "email": "rajesh.kumar@college.edu"
    },
    "updatedAt": "2026-06-20T15:00:00.000Z"
  }
}
```

**Endpoint:**

```python
@router.patch("/{id}/assign-coordinator")
async def assign_coordinator(
    id: str,
    request: AssignCoordinatorRequest,
    current_user: User = Depends(require_admin),
):
    """Assign teacher coordinator to event."""
    return await event_service.assign_coordinator(id, request.coordinatorId)
```

**Error Responses:**

| Code | Scenario |
|---|---|
| `NOT_FOUND` | Event or user not found |
| `VALIDATION_ERROR` | `coordinatorId` is not a valid UUID |
| `CONFLICT` | User is not a teacher or status is not `active` |

---

### 9.8 POST /events/{id}/brochure

Request a presigned S3 upload URL for an event brochure. The student creator of an `out_college` event can upload a brochure/event poster.

**Authentication:** Required  
**Authorization:** Student creator of the event; event must be `out_college`

**Path Parameters:**

| Param | Type | Description |
|---|---|---|
| `id` | `uuid` (path) | Event ID |

**Pydantic Schema:**

```python
from enum import Enum


class AllowedMimeType(str, Enum):
    jpeg = "image/jpeg"
    png = "image/png"
    webp = "image/webp"
    pdf = "application/pdf"


class BrochureUploadRequest(BaseModel):
    fileName: str        # Original file name with extension (e.g., "poster.png")
    fileType: AllowedMimeType  # MIME type

    @field_validator("fileName")
    @classmethod
    def validate_filename(cls, v: str) -> str:
        import re
        stripped = v.strip()
        if not stripped:
            raise ValueError("File name is required")
        if len(stripped) > 255:
            raise ValueError("File name too long")
        if not re.match(r"^[a-zA-Z0-9_.-]+$", stripped):
            raise ValueError("File name contains invalid characters")
        return stripped
```

**Allowed MIME Types:** `image/jpeg`, `image/png`, `image/webp`, `application/pdf`

**Response `200 OK`:**

```json
{
  "success": true,
  "data": {
    "uploadUrl": "https://s3.region.amazonaws.com/bucket/uploads/uuid/file-uuid.png?X-Amz-Algorithm=...&X-Amz-Signature=...",
    "fileKey": "uploads/uuid/file-uuid.png",
    "expiresIn": 300
  }
}
```

**Client Flow:**

1. Client calls `POST /events/{id}/brochure` to get a presigned URL.
2. Client uploads the file directly to S3 using `PUT` with the `uploadUrl`.
3. Client optionally calls `PATCH /events/{id}` to save the `fileKey` or the server can attach it automatically.

**Endpoint:**

```python
@router.post("/{id}/brochure")
async def get_brochure_upload_url(
    id: str,
    request: BrochureUploadRequest,
    current_user: User = Depends(get_current_user),
):
    """Get a presigned S3 URL for brochure upload."""
    return await event_service.get_brochure_upload_url(id, request, current_user)
```

**Error Responses:**

| Code | Scenario |
|---|---|
| `FORBIDDEN` | User is not the event creator or event is not `out_college` |
| `VALIDATION_ERROR` | Invalid `fileType` (not in allowed MIME types) |

---

## 10. Module: Registrations (`/api/v1/registrations`)

```python
router = APIRouter(prefix="/api/v1/registrations", tags=["registrations"])
```

### 10.1 POST /registrations

Register the authenticated student for an event.

**Authentication:** Required  
**Authorization:** `student` only

**Pydantic Schema:**

```python
class RegisterRequest(BaseModel):
    eventId: str                                    # UUID of the event
    roleType: RegistrationRole                      # "volunteer" or "participant"
```

**Validation Rules:**

| Condition | Behavior |
|---|---|
| Event status is `approved` | Proceed |
| Event status is not `approved` | Return `EVENT_NOT_APPROVED` (409) |
| Registration count >= `maxRegistrations` (if > 0) | Return `EVENT_FULL` (409) |
| Duplicate `(eventId, studentId, roleType)` | Return `CONFLICT` (409) |
| Dual registration (same event, different role) | Allowed — student can be both `volunteer` and `participant` |

**Response `201 Created`:**

```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "eventId": "uuid",
    "studentId": "uuid",
    "roleType": "participant",
    "status": "pending",
    "registeredAt": "2026-06-20T16:00:00.000Z"
  }
}
```

**Endpoint:**

```python
@router.post("", status_code=status.HTTP_201_CREATED)
async def register_for_event(
    request: RegisterRequest,
    current_user: User = Depends(get_current_user),
):
    """Register authenticated student for an event."""
    return await registration_service.register(request, current_user)
```

**Error Responses:**

| Code | Scenario |
|---|---|
| `VALIDATION_ERROR` | Invalid `eventId` or `roleType` |
| `EVENT_NOT_APPROVED` | Event status is not `approved` |
| `EVENT_FULL` | Event has reached `maxRegistrations` |
| `CONFLICT` | Already registered for this event with the same role |
| `NOT_FOUND` | Event not found |

---

### 10.2 GET /registrations/my

List the authenticated student's registrations.

**Authentication:** Required  
**Authorization:** `student` only

**Query Parameters:**

| Param | Type | Default | Description |
|---|---|---|---|
| `status` | `RegistrationStatus` (query) | — | Filter by status (`pending`, `accepted`, `rejected`) |
| `page` | `int` (query) | 1 | Page number |
| `limit` | `int` (query) | 20 | Items per page (max 100) |

**Response `200 OK`:**

```json
{
  "success": true,
  "data": [
    {
      "id": "uuid",
      "eventId": "uuid",
      "event": {
        "id": "uuid",
        "title": "Annual Tech Fest 2026",
        "type": "in_college",
        "startDate": "2026-07-04T00:00:00.000Z",
        "endDate": "2026-07-05T00:00:00.000Z"
      },
      "roleType": "participant",
      "status": "accepted",
      "registeredAt": "2026-06-19T10:00:00.000Z"
    }
  ],
  "meta": {
    "page": 1,
    "limit": 20,
    "total": 2,
    "totalPages": 1
  }
}
```

**Endpoint:**

```python
@router.get("/my", response_model=SuccessResponse[list[RegistrationResponse]])
async def get_my_registrations(
    pagination: PaginationParams = Depends(),
    status: Optional[RegistrationStatus] = Query(None),
    current_user: User = Depends(get_current_user),
):
    """List current student's registrations."""
    return await registration_service.get_my_registrations(
        current_user, pagination=pagination, status_filter=status
    )
```

---

### 10.3 GET /registrations/event/{eventId}

List all registrations for a specific event. Used by coordinators to view registered students.

**Authentication:** Required  
**Authorization:** Teacher (assigned coordinator) or `admin`

**Path Parameters:**

| Param | Type | Description |
|---|---|---|
| `eventId` | `uuid` (path) | Event ID |

**Query Parameters:**

| Param | Type | Default | Description |
|---|---|---|---|
| `status` | `RegistrationStatus` (query) | — | Filter by status (`pending`, `accepted`, `rejected`) |
| `page` | `int` (query) | 1 | Page number |
| `limit` | `int` (query) | 20 | Items per page (max 100) |

**Response `200 OK`:**

```json
{
  "success": true,
  "data": [
    {
      "id": "uuid",
      "eventId": "uuid",
      "student": {
        "id": "uuid",
        "name": "Priya Singh",
        "email": "priya.singh@college.edu"
      },
      "roleType": "participant",
      "status": "accepted",
      "registeredAt": "2026-06-19T10:00:00.000Z"
    }
  ],
  "meta": {
    "page": 1,
    "limit": 20,
    "total": 15,
    "totalPages": 1
  }
}
```

**Endpoint:**

```python
@router.get("/event/{eventId}", response_model=SuccessResponse[list[RegistrationWithStudentResponse]])
async def get_event_registrations(
    eventId: str,
    pagination: PaginationParams = Depends(),
    status: Optional[RegistrationStatus] = Query(None),
    current_user: User = Depends(get_current_user),
):
    """List all registrations for a specific event."""
    return await registration_service.get_event_registrations(
        eventId, current_user, pagination=pagination, status_filter=status
    )
```

**Error Responses:**

| Code | Scenario |
|---|---|
| `NOT_FOUND` | Event not found |
| `FORBIDDEN` | Teacher is not the assigned coordinator |

---

### 10.4 PATCH /registrations/{id}/accept

Accept a pending registration.

**Authentication:** Required  
**Authorization:** Teacher (assigned coordinator) or `admin`

**Path Parameters:**

| Param | Type | Description |
|---|---|---|
| `id` | `uuid` (path) | Registration ID |

**Response `200 OK`:**

```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "eventId": "uuid",
    "studentId": "uuid",
    "roleType": "participant",
    "status": "accepted",
    "updatedAt": "2026-06-20T17:00:00.000Z"
  }
}
```

**Endpoint:**

```python
@router.patch("/{id}/accept", response_model=SuccessResponse[RegistrationResponse])
async def accept_registration(
    id: str,
    current_user: User = Depends(get_current_user),
):
    """Accept a pending registration."""
    return await registration_service.accept_registration(id, current_user)
```

**Error Responses:**

| Code | Scenario |
|---|---|
| `NOT_FOUND` | Registration not found |
| `FORBIDDEN` | Teacher is not the coordinator of the event |
| `CONFLICT` | Registration status is not `pending` |

---

### 10.5 PATCH /registrations/{id}/reject

Reject a pending registration.

**Authentication:** Required  
**Authorization:** Teacher (assigned coordinator) or `admin`

**Path Parameters:**

| Param | Type | Description |
|---|---|---|
| `id` | `uuid` (path) | Registration ID |

**Response `200 OK`:**

```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "eventId": "uuid",
    "studentId": "uuid",
    "roleType": "participant",
    "status": "rejected",
    "updatedAt": "2026-06-20T17:00:00.000Z"
  }
}
```

**Endpoint:**

```python
@router.patch("/{id}/reject", response_model=SuccessResponse[RegistrationResponse])
async def reject_registration(
    id: str,
    current_user: User = Depends(get_current_user),
):
    """Reject a pending registration."""
    return await registration_service.reject_registration(id, current_user)
```

**Error Responses:**

| Code | Scenario |
|---|---|
| `NOT_FOUND` | Registration not found |
| `FORBIDDEN` | Teacher is not the coordinator of the event |
| `CONFLICT` | Registration status is not `pending` |

---

### 10.6 POST /registrations/{id}/proof

Request a presigned S3 upload URL for uploading proof/document related to the registration (e.g., ID card for out-college events).

**Authentication:** Required  
**Authorization:** Student who owns the registration

**Path Parameters:**

| Param | Type | Description |
|---|---|---|
| `id` | `uuid` (path) | Registration ID |

**Pydantic Schema:**

```python
class ProofUploadRequest(BaseModel):
    fileName: str                               # Original file name with extension
    fileType: AllowedMimeType                   # MIME type

    @field_validator("fileName")
    @classmethod
    def validate_filename(cls, v: str) -> str:
        import re
        stripped = v.strip()
        if not stripped:
            raise ValueError("File name is required")
        if len(stripped) > 255:
            raise ValueError("File name too long")
        if not re.match(r"^[a-zA-Z0-9_.-]+$", stripped):
            raise ValueError("File name contains invalid characters")
        return stripped
```

**Allowed MIME Types:** `image/jpeg`, `image/png`, `image/webp`, `application/pdf`

**Response `200 OK`:**

```json
{
  "success": true,
  "data": {
    "uploadUrl": "https://s3.region.amazonaws.com/bucket/proofs/uuid/file-uuid.pdf?X-Amz-Algorithm=...&X-Amz-Signature=...",
    "fileKey": "proofs/uuid/file-uuid.pdf",
    "expiresIn": 300
  }
}
```

**Endpoint:**

```python
@router.post("/{id}/proof")
async def get_proof_upload_url(
    id: str,
    request: ProofUploadRequest,
    current_user: User = Depends(get_current_user),
):
    """Get a presigned S3 URL for proof upload."""
    return await registration_service.get_proof_upload_url(id, request, current_user)
```

**Error Responses:**

| Code | Scenario |
|---|---|
| `FORBIDDEN` | Student does not own this registration |
| `NOT_FOUND` | Registration not found |

---

## 11. Module: Attendance (`/api/v1/attendance`)

```python
router = APIRouter(prefix="/api/v1/attendance", tags=["attendance"])
```

### 11.1 POST /attendance/mark

Mark attendance for a single student on a specific event date.

**Authentication:** Required  
**Authorization:** Teacher (assigned coordinator of the event)

**Rate limited:** Yes (30/min per user)

**Pydantic Schema:**

```python
from datetime import date


class MarkAttendanceRequest(BaseModel):
    eventId: str       # UUID of the event
    studentId: str     # UUID of the student
    date: date         # ISO 8601 date (YYYY-MM-DD)
    present: bool      # true = present, false = absent
```

**Response `201 Created`:**

```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "eventId": "uuid",
    "studentId": "uuid",
    "date": "2026-07-04",
    "status": "present",
    "markedBy": "uuid",
    "markedAt": "2026-07-04T10:00:00.000Z"
  }
}
```

**Note:** The `present: bool` field maps to `AttendanceStatus` as `true` → `present`, `false` → `absent`. The `late` status is not settable via this endpoint and requires a direct PATCH.

**Endpoint:**

```python
@router.post("/mark", status_code=status.HTTP_201_CREATED)
async def mark_attendance(
    request: MarkAttendanceRequest,
    current_user: User = Depends(get_current_user),
):
    """Mark attendance for a single student."""
    return await attendance_service.mark_attendance(request, current_user)
```

**Error Responses:**

| Code | Scenario |
|---|---|
| `VALIDATION_ERROR` | Invalid eventId, studentId, or date |
| `FORBIDDEN` | Teacher is not the assigned coordinator |
| `NOT_FOUND` | Event or student not found |
| `CONFLICT` | Attendance record already exists for this student/event/date |

---

### 11.2 POST /attendance/bulk

Mark attendance for multiple students at once for a specific event and date. Uses upsert — existing records are updated, new records are created.

**Authentication:** Required  
**Authorization:** Teacher (assigned coordinator of the event)

**Rate limited:** Yes (30/min per user)

**Pydantic Schema:**

```python
from pydantic import model_validator


class AttendanceRecord(BaseModel):
    studentId: str
    present: bool


class BulkAttendanceRequest(BaseModel):
    eventId: str
    date: date                                     # YYYY-MM-DD
    records: list[AttendanceRecord]                # Min 1, max 100 entries

    @model_validator(mode="after")
    def check_duplicate_students(self) -> "BulkAttendanceRequest":
        student_ids = [r.studentId for r in self.records]
        if len(student_ids) != len(set(student_ids)):
            raise ValueError("Duplicate student IDs in batch")
        return self

    @field_validator("records")
    @classmethod
    def validate_records_count(cls, v: list) -> list:
        if len(v) < 1:
            raise ValueError("At least one record is required")
        if len(v) > 100:
            raise ValueError("Maximum 100 records per batch")
        return v
```

**Validation Rules:**

| Rule | Behavior |
|---|---|
| `records` array | Min 1, max 100 entries |
| Duplicate `studentId` in batch | Return `VALIDATION_ERROR` |
| All students must be registered for this event | Return `VALIDATION_ERROR` with details |

**Response `200 OK`:**

```json
{
  "success": true,
  "data": {
    "count": 45,
    "message": "Attendance marked for 45 students"
  }
}
```

**Endpoint:**

```python
@router.post("/bulk", response_model=SuccessResponse[BulkAttendanceResponse])
async def mark_bulk_attendance(
    request: BulkAttendanceRequest,
    current_user: User = Depends(get_current_user),
):
    """Mark attendance for multiple students (upsert)."""
    return await attendance_service.mark_bulk_attendance(request, current_user)
```

**Error Responses:**

| Code | Scenario |
|---|---|
| `VALIDATION_ERROR` | Invalid records or duplicate studentIds in batch |
| `FORBIDDEN` | Teacher is not the assigned coordinator |
| `NOT_FOUND` | Event not found |

---

### 11.3 GET /attendance/event/{eventId}

Get the attendance sheet for a specific event.

**Authentication:** Required  
**Authorization:** Teacher (assigned coordinator) or `admin`

**Path Parameters:**

| Param | Type | Description |
|---|---|---|
| `eventId` | `uuid` (path) | Event ID |

**Query Parameters:**

| Param | Type | Default | Description |
|---|---|---|---|
| `date` | `str` (YYYY-MM-DD) (query) | — | Filter by specific date. If omitted, returns all dates. |
| `page` | `int` (query) | 1 | Page number |
| `limit` | `int` (query) | 20 | Items per page (max 100) |

**Response `200 OK`:**

```json
{
  "success": true,
  "data": [
    {
      "id": "uuid",
      "eventId": "uuid",
      "student": {
        "id": "uuid",
        "name": "Priya Singh",
        "email": "priya.singh@college.edu"
      },
      "date": "2026-07-04",
      "status": "present",
      "markedBy": "uuid",
      "markedAt": "2026-07-04T10:00:00.000Z"
    }
  ],
  "meta": {
    "page": 1,
    "limit": 20,
    "total": 45,
    "totalPages": 3
  }
}
```

**Endpoint:**

```python
@router.get("/event/{eventId}", response_model=SuccessResponse[list[AttendanceResponse]])
async def get_event_attendance(
    eventId: str,
    pagination: PaginationParams = Depends(),
    date: Optional[str] = Query(None, regex=r"^\d{4}-\d{2}-\d{2}$"),
    current_user: User = Depends(get_current_user),
):
    """Get attendance sheet for an event."""
    return await attendance_service.get_event_attendance(
        eventId, current_user, pagination=pagination, date=date
    )
```

**Error Responses:**

| Code | Scenario |
|---|---|
| `NOT_FOUND` | Event not found |
| `FORBIDDEN` | Teacher is not the assigned coordinator |

---

### 11.4 GET /attendance/student/{studentId}

Get a student's attendance records across all events.

**Authentication:** Required  
**Authorization:** Student (own records only) or `admin`

**Path Parameters:**

| Param | Type | Description |
|---|---|---|
| `studentId` | `uuid` (path) | Student's user ID |

**Query Parameters:**

| Param | Type | Default | Description |
|---|---|---|---|
| `page` | `int` (query) | 1 | Page number |
| `limit` | `int` (query) | 20 | Items per page (max 100) |

**Response `200 OK`:**

```json
{
  "success": true,
  "data": [
    {
      "id": "uuid",
      "event": {
        "id": "uuid",
        "title": "Freshers Welcome 2026"
      },
      "date": "2026-06-13",
      "status": "present",
      "markedAt": "2026-06-13T10:00:00.000Z"
    }
  ],
  "meta": {
    "page": 1,
    "limit": 20,
    "total": 1,
    "totalPages": 1
  }
}
```

**Endpoint:**

```python
@router.get("/student/{studentId}", response_model=SuccessResponse[list[AttendanceWithEventResponse]])
async def get_student_attendance(
    studentId: str,
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(get_current_user),
):
    """Get a student's attendance records."""
    return await attendance_service.get_student_attendance(
        studentId, current_user, pagination=pagination
    )
```

**Error Responses:**

| Code | Scenario |
|---|---|
| `FORBIDDEN` | Student trying to access another student's records |
| `NOT_FOUND` | Student not found |

---

## 12. Python Enum Reference

These enums are used throughout the API for validation and data modeling.

```python
from enum import Enum


class Role(str, Enum):
    student = "student"
    teacher = "teacher"
    admin = "admin"


class UserStatus(str, Enum):
    pending = "pending"
    active = "active"
    rejected = "rejected"


class EventType(str, Enum):
    in_college = "in_college"
    out_college = "out_college"


class EventCategory(str, Enum):
    volunteer = "volunteer"
    participant = "participant"
    both = "both"


class EventStatus(str, Enum):
    draft = "draft"
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class RegistrationRole(str, Enum):
    volunteer = "volunteer"
    participant = "participant"


class RegistrationStatus(str, Enum):
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"


class AttendanceStatus(str, Enum):
    present = "present"
    absent = "absent"
    late = "late"
```

---

## 13. Full Pydantic Response Models

### 13.1 User

```python
from pydantic import BaseModel
from datetime import datetime


class UserResponse(BaseModel):
    id: str                        # UUID
    name: str                      # VarChar(120)
    email: str                     # VarChar(180), unique
    role: Role                     # "student" | "teacher" | "admin"
    status: UserStatus             # "pending" | "active" | "rejected"
    createdAt: datetime            # ISO 8601
    updatedAt: datetime            # ISO 8601
```

### 13.2 Event

```python
class EventResponse(BaseModel):
    id: str                                    # UUID
    title: str                                 # VarChar(200)
    description: Optional[str] = None          # Text
    type: EventType                            # "in_college" | "out_college"
    category: EventCategory                    # "volunteer" | "participant" | "both"
    status: EventStatus                        # "draft" | "pending" | "approved" | "rejected"
    venue: str                                 # VarChar(300)
    startDate: datetime                        # ISO 8601
    endDate: datetime                          # ISO 8601
    maxRegistrations: int                      # Integer, 0 = unlimited
    registrationCount: Optional[int] = None    # Computed (list and detail responses)
    attendanceCount: Optional[int] = None      # Computed (detail response only)
    createdBy: Union[str, UserRef]             # UUID or populated object
    coordinatorId: str                         # UUID
    coordinator: Optional[UserRef] = None      # Populated in detail responses
    createdAt: datetime
    updatedAt: datetime


class UserRef(BaseModel):
    id: str
    name: str
    email: Optional[str] = None
```

### 13.3 Registration

```python
class RegistrationResponse(BaseModel):
    id: str                                    # UUID
    eventId: str                               # UUID
    event: Optional[EventRef] = None           # Populated in list responses
    studentId: str                             # UUID
    student: Optional[UserRef] = None          # Populated in event-level list responses
    roleType: RegistrationRole                 # "volunteer" | "participant"
    status: RegistrationStatus                 # "pending" | "accepted" | "rejected"
    registeredAt: datetime
    updatedAt: datetime
```

### 13.4 Attendance

```python
class AttendanceResponse(BaseModel):
    id: str                                    # UUID
    eventId: str                               # UUID
    event: Optional[EventRef] = None           # Populated in student-level responses
    studentId: str                             # UUID
    student: Optional[UserRef] = None          # Populated in event-level responses
    markedBy: str                              # UUID
    date: date                                 # YYYY-MM-DD
    status: AttendanceStatus                   # "present" | "absent" | "late"
    markedAt: datetime
```

---

## 14. Common Headers

### 14.1 Request Headers

| Header | Required | Description |
|---|---|---|
| `Authorization` | For authenticated endpoints | `Bearer <token>` |
| `Content-Type` | For POST/PATCH with body | `application/json` |
| `X-Request-ID` | Optional | Client-generated correlation ID; echoed in response |

### 14.2 Response Headers

| Header | Description |
|---|---|
| `X-Request-ID` | Server-generated request correlation ID (UUIDv4) |
| `X-RateLimit-Limit` | Max requests allowed in current window |
| `X-RateLimit-Remaining` | Requests remaining in current window |
| `X-RateLimit-Reset` | Unix timestamp when window resets |

---

## 15. Health Check Endpoints (Not under `/api/v1`)

| Endpoint | Purpose | Checks |
|---|---|---|
| `GET /health` | Liveness probe | Returns `200 OK` immediately |
| `GET /health/ready` | Readiness probe | Pings PostgreSQL (`SELECT 1`), Redis (`PING`); returns `200` only if both respond |

These endpoints are **not** rate-limited and **not** authenticated.

```python
from fastapi import APIRouter
from app.core.health import check_db, check_redis

health_router = APIRouter(tags=["health"])


@health_router.get("/health")
async def health():
    return {"status": "ok"}


@health_router.get("/health/ready")
async def readiness():
    db_ok = await check_db()
    redis_ok = await check_redis()
    if db_ok and redis_ok:
        return {"status": "ok", "database": "up", "redis": "up"}
    return {"status": "degraded", "database": "up" if db_ok else "down", "redis": "up" if redis_ok else "down"}
```

---

## 16. Endpoint Summary Table

| Method | Path | Auth | Role | Description |
|---|---|---|---|---|
| `POST` | `/api/v1/auth/signup` | — | — | Register student or teacher |
| `POST` | `/api/v1/auth/login` | — | — | Login with email and password |
| `POST` | `/api/v1/auth/refresh` | — | — | Refresh access token |
| `POST` | `/api/v1/auth/logout` | Required | Any | Logout and blacklist tokens |
| `GET` | `/api/v1/auth/me` | Required | Any | Get current user profile |
| `GET` | `/api/v1/users/pending-teachers` | Required | Admin | List pending teachers |
| `PATCH` | `/api/v1/users/{id}/approve` | Required | Admin | Approve teacher account |
| `PATCH` | `/api/v1/users/{id}/reject` | Required | Admin | Reject teacher account |
| `GET` | `/api/v1/users/teachers` | Required | Admin | List active teachers |
| `GET` | `/api/v1/events` | Required | Any | List events (role-filtered) |
| `POST` | `/api/v1/events` | Required | Student/Teacher/Admin | Create event |
| `GET` | `/api/v1/events/{id}` | Required | Any | Get event details |
| `PATCH` | `/api/v1/events/{id}` | Required | Creator/Admin | Update event |
| `PATCH` | `/api/v1/events/{id}/approve` | Required | Admin/Coordinator | Approve event |
| `PATCH` | `/api/v1/events/{id}/reject` | Required | Admin/Coordinator | Reject event |
| `PATCH` | `/api/v1/events/{id}/assign-coordinator` | Required | Admin | Assign teacher coordinator |
| `POST` | `/api/v1/events/{id}/brochure` | Required | Student (creator) | Get brochure upload URL |
| `POST` | `/api/v1/registrations` | Required | Student | Register for event |
| `GET` | `/api/v1/registrations/my` | Required | Student | List own registrations |
| `GET` | `/api/v1/registrations/event/{eventId}` | Required | Admin/Coordinator | List event registrations |
| `PATCH` | `/api/v1/registrations/{id}/accept` | Required | Admin/Coordinator | Accept registration |
| `PATCH` | `/api/v1/registrations/{id}/reject` | Required | Admin/Coordinator | Reject registration |
| `POST` | `/api/v1/registrations/{id}/proof` | Required | Student (owner) | Get proof upload URL |
| `POST` | `/api/v1/attendance/mark` | Required | Coordinator | Mark single attendance |
| `POST` | `/api/v1/attendance/bulk` | Required | Coordinator | Bulk mark attendance |
| `GET` | `/api/v1/attendance/event/{eventId}` | Required | Admin/Coordinator | Get attendance sheet |
| `GET` | `/api/v1/attendance/student/{studentId}` | Required | Student (own)/Admin | Get student attendance |

---

## 17. CORS Configuration

The server is configured with an explicit origin whitelist from the `CORS_ORIGINS` environment variable (comma-separated).

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,  # Parsed from env comma-separated list
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Default configurations:**

| Environment | Allowed Origins |
|---|---|
| Development | `http://localhost:5173` (Vite), `http://localhost:8000` |
| Production | College domain and trusted subdomains |

---

## 18. Environment Variables (API-relevant)

| Variable | Required | Default | Description |
|---|---|---|---|
| `HOST` | No | `0.0.0.0` | HTTP server bind address |
| `PORT` | No | `8000` | HTTP server port |
| `DATABASE_URL` | Yes | — | PostgreSQL connection string |
| `REDIS_URL` | Yes | — | Redis connection string |
| `JWT_SECRET` | Yes | — | Symmetric key for signing JWTs (min 32 chars) |
| `JWT_ACCESS_EXPIRY` | No | `15` | Access token expiry in minutes |
| `JWT_REFRESH_EXPIRY` | No | `10080` | Refresh token expiry in minutes (7 days) |
| `CORS_ORIGINS` | Yes | — | Comma-separated allowed origins |
| `RATE_LIMIT_WINDOW_MS` | No | `60000` | Rate limit window in ms |
| `RATE_LIMIT_MAX` | No | `100` | Max requests per window per IP |
| `S3_BUCKET` | Yes | — | S3 bucket name for file uploads |
| `S3_REGION` | Yes | — | AWS region |
| `S3_ACCESS_KEY` | Yes | — | AWS access key |
| `S3_SECRET_KEY` | Yes | — | AWS secret key |
| `LOG_LEVEL` | No | `INFO` | Python logging level |
