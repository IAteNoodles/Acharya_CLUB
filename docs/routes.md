# Acharya_CLUB — API Route Specification

This document details all available API endpoints, their HTTP methods, routes, handlers, and descriptions.

The base URL for all endpoints is `/api/v1`.

---

## 1. Public & Utility Endpoints

| Method | Route | Description | Handler |
|---|---|---|---|
| `GET` | `/health` | Unauthenticated application health check | `health_check` |
| `GET` | `/docs` | Swagger interactive API documentation | Swagger UI |
| `GET` | `/openapi.json` | OpenAPI JSON schema representation | OpenAPI Schema |
| `GET` | `/redoc` | ReDoc alternative documentation | ReDoc |

---

## 2. Authentication (`/auth`)

| Method | Route | Description | Handler |
|---|---|---|---|
| `POST` | `/auth/signup` | Register a new user (Student or Teacher) | `signup` |
| `POST` | `/auth/login` | Authenticate and retrieve access/refresh tokens | `login` |
| `POST` | `/auth/refresh` | Rotate access and refresh tokens | `refresh` |
| `POST` | `/auth/logout` | Revoke active session tokens | `logout` |
| `GET` | `/auth/me` | Retrieve current authenticated user profile | `me` |

---

## 3. Users (`/users`)

| Method | Route | Description | Handler |
|---|---|---|---|
| `GET` | `/users/pending-teachers` | List teacher accounts awaiting admin approval (Admin only) | `get_pending_teachers` |
| `PATCH` | `/users/{id}/approve` | Approve a pending teacher account (Admin only) | `approve_teacher` |
| `PATCH` | `/users/{id}/reject` | Reject a pending teacher account (Admin only) | `reject_teacher` |
| `GET` | `/users/teachers` | List all active approved teacher accounts (Admin only) | `get_teachers` |

---

## 4. Events (`/events`)

| Method | Route | Description | Handler |
|---|---|---|---|
| `GET` | `/events` | List events (filtered by user role/permissions) | `list_events` |
| `POST` | `/events` | Create a new event proposal | `create_event` |
| `GET` | `/events/{event_id}` | Retrieve details of a specific event | `get_event` |
| `PATCH` | `/events/{event_id}` | Update event details (Creator/Admin only) | `update_event` |
| `PATCH` | `/events/{event_id}/approve` | Approve an event proposal (Admin only) | `approve_event` |
| `PATCH` | `/events/{event_id}/reject` | Reject an event proposal (Admin only) | `reject_event` |
| `PATCH` | `/events/{event_id}/assign-coordinator` | Assign a teacher coordinator to an event (Admin only) | `assign_coordinator` |

---

## 5. Registrations (`/registrations`)

| Method | Route | Description | Handler |
|---|---|---|---|
| `POST` | `/registrations` | Register the current student for an event | `register_for_event` |
| `GET` | `/registrations/my` | List event registrations for the authenticated student | `get_my_registrations` |
| `GET` | `/registrations/event/{event_id}` | View registrations for an event (Coordinator/Admin only) | `get_event_registrations` |
| `PATCH` | `/registrations/{id}/accept` | Accept a student registration (Coordinator/Admin only) | `accept_registration` |
| `PATCH` | `/registrations/{id}/reject` | Reject a student registration (Coordinator/Admin only) | `reject_registration` |

---

## 6. Attendance (`/attendance`)

| Method | Route | Description | Handler |
|---|---|---|---|
| `POST` | `/attendance/bulk` | Mark attendance in bulk for registrations (Coordinator/Admin only) | `mark_bulk_attendance` |
| `GET` | `/attendance/event/{event_id}` | View attendance history for a specific event | `get_event_attendance` |
| `GET` | `/attendance/my` | View attendance history for the authenticated student | `get_my_attendance` |
| `GET` | `/attendance/student/{student_id}` | View attendance history for a specific student (Admin only) | `get_student_attendance` |

---

## 7. Notifications (`/notifications`)

| Method | Route | Description | Handler |
|---|---|---|---|
| `GET` | `/notifications` | List notifications for the current authenticated user | `list_notifications` |
| `GET` | `/notifications/unread-count` | Retrieve the count of unread notifications | `unread_count` |
| `PATCH` | `/notifications/{id}/read` | Mark a specific notification as read | `mark_as_read` |
| `PATCH` | `/notifications/read-all` | Mark all notifications as read | `mark_all_as_read` |

---

## 8. Reports (`/reports`)

| Method | Route | Description | Handler |
|---|---|---|---|
| `GET` | `/reports/dashboard` | Retrieve aggregate metrics and event data (Admin only) | `get_dashboard` |
