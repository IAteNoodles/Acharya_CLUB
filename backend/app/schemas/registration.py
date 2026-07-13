import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel

from app.models.registration import RegistrationRole, RegistrationStatus


class RegisterRequest(BaseModel):
    event_id: uuid.UUID
    role_type: RegistrationRole


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
