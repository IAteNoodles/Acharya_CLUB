# Reports/Dashboard — Design Spec

## Overview

Single dashboard endpoint that returns aggregated counts across all entities. Teachers and admins get a high-level snapshot of the system.

## Endpoint

**`GET /api/v1/reports/dashboard`** — Auth: `require_teacher_or_admin`

### Response shape

```json
{
    "success": true,
    "data": {
        "users": {
            "total": 100,
            "by_role": {"student": 80, "teacher": 15, "admin": 5},
            "by_status": {"pending": 5, "active": 90, "rejected": 5}
        },
        "events": {
            "total": 30,
            "by_status": {"draft": 5, "pending": 3, "approved": 20, "rejected": 2},
            "by_type": {"in_college": 10, "out_college": 20}
        },
        "registrations": {
            "total": 200,
            "by_status": {"pending": 30, "accepted": 150, "rejected": 20}
        },
        "attendance": {
            "total": 500,
            "by_status": {"present": 400, "absent": 80, "late": 20}
        },
        "notifications": {
            "total": 1000,
            "unread": 150
        }
    }
}
```

## Architecture

`ReportService.get_dashboard_stats(db)` runs 6 independent async queries concurrently via `asyncio.gather()` for the counts, then assembles the response. Each query is a `SELECT col, COUNT(*) ... GROUP BY col` on the respective table.

### Pydantic schemas (in `app/schemas/reports.py`)

- `CountByCategory(BaseModel)` — generic `{category: str, count: int}` (used internally)
- `UserStats(BaseModel)` — total, by_role: dict, by_status: dict
- `EventStats(BaseModel)` — total, by_status: dict, by_type: dict
- `RegistrationStats(BaseModel)` — total, by_status: dict
- `AttendanceStats(BaseModel)` — total, by_status: dict
- `NotificationStats(BaseModel)` — total, unread: int
- `DashboardResponse(BaseModel)` — users, events, registrations, attendance, notifications

### Service method

`ReportService.get_dashboard_stats(db: AsyncSession) -> DashboardResponse`

Runs 6 async queries:
1. `SELECT role, COUNT(*) FROM users GROUP BY role`
2. `SELECT status, COUNT(*) FROM users GROUP BY status`
3. `SELECT status, COUNT(*) FROM events GROUP BY status`
4. `SELECT event_type, COUNT(*) FROM events GROUP BY event_type`
5. `SELECT status, COUNT(*) FROM registrations GROUP BY status`
6. `SELECT status, COUNT(*) FROM attendance GROUP BY status`

And 2 scalar queries:
7. `SELECT COUNT(*) FROM notifications`
8. `SELECT COUNT(*) FROM notifications WHERE is_read = false`

All executed concurrently.

## Files

| Action | File |
|---|---|
| CREATE | `app/schemas/reports.py` |
| CREATE | `app/services/reports.py` |
| CREATE | `app/api/v1/reports.py` |
| MODIFY | `app/main.py` — register reports router + tag |
| CREATE | `tests/test_reports.py` |
