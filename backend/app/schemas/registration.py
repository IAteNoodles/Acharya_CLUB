import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator

from app.models.registration import RegistrationRole, RegistrationStatus


ALLOWED_PROOF_TYPES = {"image/jpeg", "image/png", "image/webp", "application/pdf"}


class RegisterRequest(BaseModel):
    event_id: uuid.UUID
    role_type: RegistrationRole


class ProofUploadRequest(BaseModel):
    file_name: str = Field(..., min_length=1, max_length=255)
    file_type: str = Field(..., min_length=1)

    @field_validator("file_type")
    @classmethod
    def validate_file_type(cls, v: str) -> str:
        if v not in ALLOWED_PROOF_TYPES:
            raise ValueError(f"file_type must be one of {ALLOWED_PROOF_TYPES}, got '{v}'")
        return v


class EventBrief(BaseModel):
    id: str
    title: str
    event_type: str
    start_date: datetime
    end_date: datetime

    model_config = {"from_attributes": True}


class StudentBrief(BaseModel):
    id: str
    name: str
    email: str

    model_config = {"from_attributes": True}


class RegistrationResponse(BaseModel):
    success: bool = True
    id: str
    event_id: str
    student_id: str
    role_type: str
    status: str
    registered_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RegistrationWithEventResponse(BaseModel):
    success: bool = True
    id: str
    event_id: str
    role_type: str
    status: str
    registered_at: datetime
    event: EventBrief

    model_config = {"from_attributes": True}


class RegistrationWithStudentResponse(BaseModel):
    success: bool = True
    id: str
    event_id: str
    role_type: str
    status: str
    registered_at: datetime
    student: StudentBrief

    model_config = {"from_attributes": True}


class ProofUploadResponse(BaseModel):
    success: bool = True
    upload_url: str
    file_key: str
    expires_in: int
