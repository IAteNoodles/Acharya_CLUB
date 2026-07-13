import uuid
from datetime import date
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class AttendanceRecord(BaseModel):
    studentId: uuid.UUID
    present: bool


class BulkAttendanceRequest(BaseModel):
    eventId: uuid.UUID
    date: date
    records: list[AttendanceRecord]

    @field_validator("records")
    @classmethod
    def validate_records_count(cls, v: list) -> list:
        if len(v) < 1:
            raise ValueError("At least one record is required")
        if len(v) > 100:
            raise ValueError("Maximum 100 records per batch")
        return v

    @model_validator(mode="after")
    def check_duplicate_students(self) -> "BulkAttendanceRequest":
        student_ids = [str(r.studentId) for r in self.records]
        if len(student_ids) != len(set(student_ids)):
            raise ValueError("Duplicate student IDs in batch")
        return self


class BulkAttendanceResponse(BaseModel):
    success: bool = True
    count: int
    message: str


class StudentBrief(BaseModel):
    id: str
    name: str
    email: str

    model_config = {"from_attributes": True}


class MarkerBrief(BaseModel):
    id: str
    name: str

    model_config = {"from_attributes": True}


class AttendanceRecordResponse(BaseModel):
    success: bool = True
    id: str
    event_id: str
    student_id: str
    date: date
    status: str
    marked_by: str
    marked_at: str

    model_config = {"from_attributes": True}


class AttendanceWithStudentResponse(BaseModel):
    success: bool = True
    id: str
    event_id: str
    student_id: str
    date: date
    status: str
    student: Optional[StudentBrief] = None
    marked_by: Optional[MarkerBrief] = None

    model_config = {"from_attributes": True}


class AttendanceWithEventResponse(BaseModel):
    success: bool = True
    id: str
    event_id: str
    student_id: str
    date: date
    status: str
    event: Optional[dict] = None

    model_config = {"from_attributes": True}
