# In-App Notification System — Design Spec

## Overview

Add an in-app notification system to the Acharya_CLUB backend. When a user's registration is accepted/rejected, an event is approved/rejected, or a teacher account is approved/rejected, the affected user receives an in-app notification stored in the database and viewable via API.

**No email sending.** Notifications live in the DB and are fetched by the frontend.

## Data Model

### `Notification` table

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK, default `uuid.uuid4` | |
| `user_id` | UUID | FK → users.id, NOT NULL, indexed | receiver |
| `type` | Enum(NotificationType) | NOT NULL | see enum below |
| `title` | String(200) | NOT NULL | short summary |
| `message` | Text | NOT NULL | rendered message body |
| `related_entity_type` | String(50) | nullable | `"registration"`, `"event"`, `"user"` |
| `related_entity_id` | UUID | nullable | FK not enforced (polymorphic) |
| `is_read` | Boolean | NOT NULL, default `false` | |
| `created_at` | DateTime(tz) | server default `now()` | from TimestampMixin |
| `updated_at` | DateTime(tz) | server default `now()`, onupdate | from TimestampMixin |

### `NotificationType` enum

```
registration_accepted
registration_rejected
event_approved
event_rejected
teacher_approved
teacher_rejected
```

### Notification message templates

| Type | Title | Message |
|---|---|---|
| `registration_accepted` | "Registration Accepted" | "Your registration for {event_title} as {role} has been accepted." |
| `registration_rejected` | "Registration Rejected" | "Your registration for {event_title} as {role} has been rejected." |
| `event_approved` | "Event Approved" | "Your event {event_title} has been approved by the admin." |
| `event_rejected` | "Event Rejected" | "Your event {event_title} has been rejected by the admin." |
| `teacher_approved` | "Account Approved" | "Your teacher account has been approved. You can now log in and create events." |
| `teacher_rejected` | "Account Rejected" | "Your teacher account request has been rejected." |

## Architecture

### Design Decision: Side-effect coupling in services

Notifications are created **inside the existing service methods** (Approach A). When `accept_registration()` succeeds, it also calls `NotificationService.create_notification()` in the **same DB transaction**. The notification is added to the session **before** `db.commit()`, so the status change and notification are committed together atomically.
1. Notifications are never forgotten when statuses change
2. Notification creation is atomic with the status change (rolls back together on failure)

### Dependency flow

```
Router → ExistingService.do_action()
           ├── 1. Update entity status in DB
           └── 2. NotificationService.create_notification(db, ...)
                      └── INSERT INTO notifications
```

`NotificationService` is a standalone service (static methods like the existing services). It does NOT depend on other services. Other services import and call `NotificationService.create_notification()`.

## Service Layer

### `NotificationService` (in `app/services/notification.py`)

```python
class NotificationService:
    @staticmethod
    async def create_notification(db, user_id, type, title, message, entity_type=None, entity_id=None) -> Notification

    @staticmethod
    async def get_user_notifications(db, user_id, page, limit, unread_only=False) -> tuple[list[Notification], int]

    @staticmethod
    async def mark_as_read(db, notification_id, user_id) -> Notification

    @staticmethod
    async def mark_all_as_read(db, user_id) -> int  # returns count of updated

    @staticmethod
    async def get_unread_count(db, user_id) -> int
```

### Message rendering helpers

A helper function `_render_message(type, context)` builds the title and message strings using a context dict (`event_title`, `role`, etc.). Keeps message construction DRY and testable.

## API Endpoints

All under `/api/v1/notifications`. All require authentication (any role).

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/notifications` | any | list caller's notifications, newest first. Query: `page`, `limit`, `unread_only` |
| GET | `/notifications/unread-count` | any | `{"success": true, "data": {"count": N}}` |
| PATCH | `/notifications/{id}/read` | any | mark one notification as read. Returns 404 if not found or not owned by caller |
| PATCH | `/notifications/read-all` | any | mark all of caller's unread notifications as read. Returns `{"success": true, "data": {"count": N}}` |

### Response for GET /notifications

```json
{
    "success": true,
    "data": [
        {
            "id": "uuid",
            "type": "registration_accepted",
            "title": "Registration Accepted",
            "message": "Your registration for Tech Fest as volunteer has been accepted.",
            "related_entity_type": "registration",
            "related_entity_id": "uuid",
            "is_read": false,
            "created_at": "2026-06-21T10:00:00Z"
        }
    ],
    "meta": {
        "page": 1,
        "limit": 20,
        "total": 1,
        "total_pages": 1
    }
}
```

## Integration Points

### `RegistrationService.accept_registration()` — AFTER status update
- Notify student with type `registration_accepted`

### `RegistrationService.reject_registration()` — AFTER status update
- Notify student with type `registration_rejected`

### `EventService.approve_event()` — AFTER status update
- Notify event creator with type `event_approved`

### `EventService.reject_event()` — AFTER status update
- Notify event creator with type `event_rejected`

### `UserService.approve_teacher()` — AFTER status update
- Notify teacher with type `teacher_approved`

### `UserService.reject_teacher()` — AFTER status update
- Notify teacher with type `teacher_rejected`

## Testing Strategy

### 1. Schema tests (6 tests)
- Valid notification schemas (response models)
- NotificationType enum values

### 2. Service tests (14 tests)
- `create_notification` — creates DB record, returns correct fields
- `create_notification` — invalid user_id raises IntegrityError
- `get_user_notifications` — pagination, ordering (newest first)
- `get_user_notifications` — unread_only filter
- `get_user_notifications` — empty result for wrong user
- `mark_as_read` — marks as read, returns notification
- `mark_as_read` — wrong user returns 404
- `mark_as_read` — non-existent id returns 404
- `mark_all_as_read` — marks all, returns correct count
- `mark_all_as_read` — only affects caller's notifications
- `get_unread_count` — correct count
- `get_unread_count` — returns 0 when all read

### 3. API tests (10 tests)
- GET /notifications — returns paginated list
- GET /notifications — unread_only filter
- GET /notifications/unread-count — returns count
- PATCH /{id}/read — marks as read
- PATCH /{id}/read — 404 for wrong user
- PATCH /read-all — marks all as read
- GET /notifications — 401 without auth
- PATCH /{id}/read — 401 without auth

### 4. Integration tests (12 tests)
- Accepting registration creates notification for student
- Rejecting registration creates notification for student
- Accepting registration for wrong event/student works (edge cases)
- Approving event creates notification for creator
- Rejecting event creates notification for creator
- Approving teacher creates notification for teacher
- Rejecting teacher creates notification for teacher

## Files to Create/Modify

| Action | File |
|---|---|
| CREATE | `app/models/notification.py` |
| MODIFY | `app/models/__init__.py` — add Notification, NotificationType |
| CREATE | `app/schemas/notification.py` |
| MODIFY | `app/schemas/__init__.py` — add notification schemas |
| CREATE | `app/services/notification.py` |
| MODIFY | `app/services/registration.py` — add notification call in accept/reject |
| MODIFY | `app/services/event.py` — add notification call in approve/reject |
| MODIFY | `app/services/user.py` — add notification call in approve/reject |
| CREATE | `app/api/v1/notifications.py` |
| MODIFY | `app/main.py` — register notifications router |
| CREATE | `tests/test_notifications.py` |

## Alembic Migration

Generate a new migration for the `notifications` table after model is created.
