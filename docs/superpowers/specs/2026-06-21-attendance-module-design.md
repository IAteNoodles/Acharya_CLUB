# Attendance Module — Design Specification

## 1. Overview

Attendance tracking for college events. Coordinators and admins mark which registered students attended each day of an event. Students can view their own attendance history.

## 2. Endpoints

Prefix: `/api/v1/attendance`

| Method | Path | Auth | Rate Limit | Description |
|--------|------|------|------------|-------------|
| `POST` | `/bulk` | Coordinator/Admin | 30/min per user | Bulk upsert attendance for an event on a date |
| `GET` | `/event/{eventId}` | Coordinator/Admin | — | Attendance sheet for an event, optional `date` filter |
| `GET` | `/my` | Student | — | Current student's attendance history |
| `GET` | `/student/{studentId}` | Admin | — | Any student's attendance records |

## 3. Data Model

The `Attendance` model already exists:

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID (PK) | Auto-generated |
| `event_id` | UUID (FK → events) | |
| `student_id` | UUID (FK → users) | |
| `marked_by_id` | UUID (FK → users) | Coordinator/admin who marked it |
| `date` | Date | Day of attendance |
| `status` | ENUM | `present`, `absent`, `late` |
| `marked_at` | TIMESTAMPTZ | Auto-set |

**Constraint:** Unique `(event_id, student_id, date)` — one record per student per event per day.

## 4. Request/Response Schemas

### 4.1 `POST /attendance/bulk`

**Request:**
```json
{
  "eventId": "uuid",
  "date": "2026-07-04",
  "records": [
    { "studentId": "uuid", "present": true },
    { "studentId": "uuid", "present": false }
  ]
}
```

- `present: true` → `status: "present"`, `false` → `status: "absent"` (`late` not settable via bulk)
- `records`: min 1, max 100
- No duplicate `studentId` in same batch
- All students must have an **accepted** registration for this event

**Response (200):**
```json
{
  "success": true,
  "data": {
    "count": 45,
    "message": "Attendance marked for 45 students"
  }
}
```

**Errors:** `VALIDATION_ERROR` (invalid input, duplicate studentIds, students not registered), `FORBIDDEN` (not coordinator/admin), `NOT_FOUND` (event not found)

### 4.2 `GET /attendance/event/{eventId}`

**Query:** `date` (optional, YYYY-MM-DD), pagination (`page`, `limit`)

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": "uuid",
      "date": "2026-07-04",
      "status": "present",
      "student": { "id": "uuid", "name": "Priya Singh", "email": "priya.singh@college.edu" },
      "markedBy": { "id": "uuid", "name": "Dr. Rajesh Kumar" }
    }
  ],
  "meta": { "page": 1, "limit": 20, "total": 45, "totalPages": 3 }
}
```

### 4.3 `GET /attendance/my`

**Query:** `eventId` (optional), `status` (optional), pagination

**Response:** List of attendance records with event details (title, type, dates)

### 4.4 `GET /attendance/student/{studentId}`

**Auth:** Admin only (students use `/my`)

**Query:** Pagination

**Response:** Same structure as `/my` but for the specified student

## 5. Business Logic

| Rule | Behavior |
|------|----------|
| **Registration required** | Only students with `accepted` registration can be marked |
| **Upsert** | If a record exists for `(event_id, student_id, date)`, update the status; otherwise insert |
| **Authorization** | Coordinator of the event OR admin can mark/view |
| **`present: bool` mapping** | `true` → `PRESENT`, `false` → `ABSENT` |
| **Batch dedup** | Duplicate `studentId` in same batch → 400 error |
| **Batch size** | 1–100 records per batch |

## 6. Files to Create

| File | Purpose |
|------|---------|
| `app/schemas/attendance.py` | Pydantic schemas |
| `app/services/attendance.py` | Service class with business logic |
| `app/api/v1/attendance.py` | FastAPI router |
| `tests/test_attendance.py` | Tests |

## 7. Files to Modify

| File | Change |
|------|--------|
| `app/api/v1/__init__.py` or `router.py` | Include attendance router |
| `app/main.py` | Register router (via existing pattern) |
| `docs/api-specification.md` | Update section 11 to reflect actual implementation |

## 8. Testing Strategy

- **Unit tests:** Schema validation (invalid batch, duplicate studentIds, missing fields)
- **Service tests:** Mock `AsyncSession`, test all rules (not registered → error, coordinator bypass, admin bypass, upsert behavior)
- **API tests:** HTTP status codes, auth failures, response structure via `httpx.AsyncClient`
- ~36–40 tests expected
