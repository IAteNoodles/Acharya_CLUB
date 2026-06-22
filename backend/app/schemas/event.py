from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from typing import Optional


class EventCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    event_type: str
    category: str
    venue: str = Field(..., min_length=1, max_length=300)
    start_date: datetime
    end_date: datetime

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        if v not in ("in_college", "out_college"):
            raise ValueError("event_type must be 'in_college' or 'out_college'")
        return v

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        if v not in ("volunteer", "participant", "both"):
            raise ValueError("category must be 'volunteer', 'participant', or 'both'")
        return v


class EventUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    category: Optional[str] = None
    venue: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("volunteer", "participant", "both"):
            raise ValueError("category must be 'volunteer', 'participant', or 'both'")
        return v


class EventApprove(BaseModel):
    admin_comment: Optional[str] = None


class EventReject(BaseModel):
    admin_comment: str = Field(..., min_length=1)


class EventAssignCoordinator(BaseModel):
    coordinator_id: str

    @field_validator("coordinator_id")
    @classmethod
    def validate_uuid(cls, v: str) -> str:
        import uuid
        uuid.UUID(v)
        return v


class UserBrief(BaseModel):
    id: str
    name: str
    email: str

    model_config = {"from_attributes": True}


class EventOut(BaseModel):
    success: bool = True
    id: str
    title: str
    description: Optional[str] = None
    event_type: str
    category: str
    status: str
    venue: Optional[str] = None
    start_date: datetime
    end_date: datetime
    max_registrations: int
    created_by: Optional[UserBrief] = None
    coordinator: Optional[UserBrief] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EventListItem(BaseModel):
    success: bool = True
    id: str
    title: str
    event_type: str
    category: str
    status: str
    start_date: datetime
    end_date: datetime
    registration_count: int = 0
    created_by_name: Optional[str] = None

    model_config = {"from_attributes": True}


class PaginatedResponse(BaseModel):
    success: bool = True
    items: list
    total: int
    page: int
    limit: int
    total_pages: int
