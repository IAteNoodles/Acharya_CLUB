from pydantic import BaseModel


class UserStats(BaseModel):
    total: int
    by_role: dict
    by_status: dict
    by_role_status: dict


class EventStats(BaseModel):
    total: int
    by_status: dict
    by_type: dict


class RegistrationStats(BaseModel):
    total: int
    by_status: dict


class AttendanceStats(BaseModel):
    total: int
    by_status: dict


class NotificationStats(BaseModel):
    total: int
    unread: int


class DashboardResponse(BaseModel):
    users: UserStats
    events: EventStats
    registrations: RegistrationStats
    attendance: AttendanceStats
    notifications: NotificationStats
