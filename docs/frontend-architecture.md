# Frontend Architecture & Implementation Plan — Acharya_CLUB

React SPA for the Acharya_CLUB College Event Management System.
This document is the frontend counterpart of `EXPLAIN.md`: what to build, how it is
structured, every page and flow, and exactly how it talks to the FastAPI backend in
`backend/`.

**Sources of truth, in priority order:**

1. The actual backend code (`backend/app/api/v1/*`, `backend/app/schemas/*`,
   `backend/app/services/*`) — every contract in this document was verified against it.
2. `Acharya_club.pdf` — the product vision (portals, navigation, color coding, UX flows).
3. `docs/api-specification.md` — **treat as aspirational**; it diverges from the code in
   field casing, several endpoints, and error codes. Where this document and that one
   disagree, this one is correct.

> ⚠️ The PDF describes a Node/Express/Prisma backend with S3 uploads, OTP email, and a
> `POST /attendance/mark` endpoint. None of that exists. The real backend is FastAPI at
> `/api/v1` with JWT rotation, in-app notifications, and a reports dashboard. Section 12
> lists every PDF feature that has no backend support and what to do about each.

---

## 1. Tech stack

| Layer | Choice | Why |
|---|---|---|
| Framework | **React 18 + Vite + TypeScript** | PDF-specified; Vite dev server on `:5173` is already in the backend's default `CORS_ORIGINS` |
| Routing | **React Router v6** (data-router, `createBrowserRouter`) | Role-based nested layouts, loaders not required — guards are components |
| Server state | **TanStack Query v5** | Caching, invalidation, pagination, polling (notifications badge) — eliminates hand-rolled fetch state |
| Client state | **Zustand** (auth/session store only) | PDF-specified; the only true global client state is the session |
| Forms + validation | **React Hook Form + Zod** | PDF-specified; Zod schemas double as request-shape documentation |
| HTTP | **Axios** with interceptors | Token attach + single-flight refresh rotation + envelope/error normalization |
| Styling | **Tailwind CSS + shadcn/ui** | PDF-specified; shadcn gives Table, Dialog, Sheet, Tabs, Toast, Badge, Calendar out of the box |
| Icons | lucide-react | ships with shadcn |
| Dates | date-fns | day-range generation for attendance, formatting |
| Tests | **Vitest + React Testing Library + MSW** | MSW mocks the real envelope shapes so tests exercise the normalization layer |

Deliberately **not** used: Redux (overkill), Next.js (no SSR need; backend serves the API,
SPA is fine), Socket/SSE (backend has none — notifications poll instead).

## 2. Repo placement & tooling

```
Acharya_CLUB/
├── backend/          # existing FastAPI app (untouched)
└── frontend/         # NEW — everything below lives here
```

- `frontend/` is a standalone Vite workspace with its own `package.json`.
- Dev: `npm run dev` on `http://localhost:5173`, calling the backend at
  `http://localhost:8000/api/v1` (env: `VITE_API_BASE_URL`). No proxy needed — CORS
  already allows `:5173` (`allow_credentials=True`, all methods/headers).
- Prod: `npm run build` → static `dist/`; serve via nginx (or any static host). Add a
  `frontend` service to `docker-compose.yml` later (Phase 6).
- **Frontend follows normal frontend hygiene** (ESLint + Prettier are fine here — the
  repo's "no linters" rule is a *backend CI* decision recorded in
  `docs/codebase/CONCERNS.md`; do not add lint steps to the backend CI job, give the
  frontend its own CI job if/when wanted).

### `.env` (frontend)

```
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

## 3. Directory structure

```
frontend/
├── index.html
├── vite.config.ts
├── tailwind.config.ts
├── .env.example
└── src/
    ├── main.tsx                  # QueryClientProvider, RouterProvider, Toaster
    ├── App.tsx
    ├── api/                      # ALL backend knowledge lives here — nothing above this
    │   │                         # layer ever sees a raw envelope or snake/camel quirk
    │   ├── client.ts             # axios instance + auth/refresh/error interceptors
    │   ├── envelopes.ts          # normalizers for the 3 envelope styles (see §5)
    │   ├── errors.ts             # ApiError type + toApiError() (see §6)
    │   ├── auth.api.ts
    │   ├── users.api.ts
    │   ├── events.api.ts
    │   ├── registrations.api.ts
    │   ├── attendance.api.ts
    │   ├── notifications.api.ts
    │   └── reports.api.ts
    ├── types/
    │   ├── enums.ts              # verbatim backend enum values (see §4)
    │   └── domain.ts             # User, Event, Registration, Attendance, Notification…
    ├── stores/
    │   └── auth.store.ts         # Zustand: user, tokens, login/logout/refresh actions
    ├── hooks/                    # TanStack Query hooks, one file per domain
    │   ├── useAuth.ts
    │   ├── useEvents.ts
    │   ├── useRegistrations.ts
    │   ├── useAttendance.ts
    │   ├── useNotifications.ts
    │   ├── useReports.ts
    │   └── useUsers.ts
    ├── router/
    │   ├── index.tsx             # route table (see §7)
    │   ├── ProtectedRoute.tsx    # authed? else → /login (preserves intended path)
    │   └── RoleRoute.tsx         # role ∈ allowed? else → /forbidden (or own dashboard)
    ├── layouts/
    │   ├── AuthLayout.tsx        # two-column: branding left / form right (PDF §5.2)
    │   └── PortalLayout.tsx      # sidebar (desktop) / bottom-nav (mobile) + topbar
    ├── components/
    │   ├── ui/                   # shadcn/ui generated primitives
    │   ├── common/               # StatusBadge, EmptyState, ConfirmDialog, Paginator,
    │   │                         # PageHeader, StatCard, SearchInput, DataTable
    │   ├── events/               # EventCard, EventStatusChip, EventForm,
    │   │                         # AssignCoordinatorDialog, ApproveRejectDialog
    │   ├── registrations/        # JoinEventSheet, RegistrationRow, BulkActionBar
    │   ├── attendance/           # DayPicker, AttendanceGrid, AttendanceToggle
    │   └── notifications/        # NotificationBell, NotificationList, NotificationItem
    ├── pages/
    │   ├── auth/                 # LoginPage, SignupPage
    │   ├── student/              # Dashboard, Events, EventDetail, Participation,
    │   │                         # Volunteering, MyRequests, MyAttendance
    │   ├── teacher/              # Dashboard, Events, EventDetail (tabs)
    │   ├── admin/                # Dashboard, Events, EventDetail, AdminPanel
    │   ├── shared/               # NotificationsPage, ProfilePage
    │   └── system/               # NotFound, Forbidden
    └── lib/
        ├── constants.ts          # status→color map (PDF §10), page sizes
        ├── format.ts             # date/time formatters
        └── utils.ts              # cn(), eventDays(start,end), etc.
```

**The one hard layering rule** (mirror of the backend's): pages/components never import
axios or touch envelope shapes — they call hooks; hooks call `api/*` functions; only
`api/*` knows the wire format. This is what makes the backend's envelope inconsistencies
(§5) a non-problem for the UI.

## 4. Domain types & enums (verbatim backend values)

All enum **values** are lowercase snake_case strings — exactly these, no others:

```ts
export type Role               = 'student' | 'teacher' | 'admin';
export type UserStatus         = 'pending' | 'active' | 'rejected';
export type EventType          = 'in_college' | 'out_college';
export type EventCategory      = 'volunteer' | 'participant' | 'both';
export type EventStatus        = 'draft' | 'pending' | 'approved' | 'rejected';
export type RegistrationRole   = 'volunteer' | 'participant';
export type RegistrationStatus = 'pending' | 'accepted' | 'rejected';
export type AttendanceStatus   = 'present' | 'absent' | 'late';   // 'late' read-only: API never writes it
export type NotificationType =
  | 'registration_accepted' | 'registration_rejected'
  | 'event_approved'        | 'event_rejected'
  | 'teacher_approved'      | 'teacher_rejected';
```

Core normalized entities (post-normalization — see §5 for what the wire actually sends):

```ts
interface User { id: string; name: string; email: string; role: Role; status: UserStatus; }

interface UserBrief { id: string; name: string; email: string; }

interface Event {
  id: string; title: string; description: string | null;
  event_type: EventType; category: EventCategory; status: EventStatus;
  venue: string | null; start_date: string; end_date: string;
  max_registrations: number;                    // 0 = unlimited; NOT settable via API (see §12)
  created_by: UserBrief | null; coordinator: UserBrief | null;
  created_at: string; updated_at: string;
}

interface EventListItem {                       // GET /events returns a slimmer shape
  id: string; title: string; event_type: EventType; category: EventCategory;
  status: EventStatus; start_date: string; end_date: string;
  registration_count: number; created_by_name: string | null;
}

interface Registration {
  id: string; event_id: string; student_id?: string;
  role_type: RegistrationRole; status: RegistrationStatus; registered_at: string;
  event?: { id: string; title: string; event_type: EventType; start_date: string; end_date: string };
  student?: UserBrief;                          // present on coordinator/admin views
}

interface AttendanceRecord {
  id: string; event_id: string; student_id: string; date: string;
  status: AttendanceStatus;
  student?: UserBrief | null; marked_by?: { id: string; name: string } | null;
  event?: { id: string; title: string; event_type: string; start_date: string; end_date: string } | null;
}

interface AppNotification {
  id: string; type: NotificationType; title: string; message: string;
  related_entity_type: 'event' | 'registration' | 'user' | null;
  related_entity_id: string | null; is_read: boolean; created_at: string;
}

interface Paginated<T> { items: T[]; page: number; limit: number; total: number; total_pages: number; }
```

**Field-casing rule (memorize):** responses are snake_case everywhere. camelCase appears
in exactly three places, all of which the `api/` layer hides:
- auth token fields: `accessToken`, `refreshToken` (responses **and** the refresh/logout request body);
- attendance bulk request body: `eventId`, `studentId`, `present`, `records`;
- attendance query param `eventId` on `GET /attendance/my`.

## 5. The API layer — normalizing three envelope styles

The backend has one error envelope but **three success envelope styles** (a documented
legacy inconsistency). The `api/envelopes.ts` normalizers collapse them so hooks/pages
only ever see `T` or `Paginated<T>`:

| Style | Used by | Wire shape | Normalizer |
|---|---|---|---|
| **Canonical single** | auth, registrations, attendance, notifications, reports, users actions | `{ success, data: T }` | `unwrapData(res)` |
| **Canonical paginated** | registrations, attendance, notifications lists | `{ success, data: T[], meta: { page, limit, total, total_pages } }` | `unwrapPaginated(res)` |
| **Legacy flat list — events** | `GET /events` | `{ success, items: T[], total, page, limit, total_pages }` | `unwrapLegacyList(res, 'items')` |
| **Legacy flat list — users** | `GET /users/pending-teachers`, `GET /users/teachers` | `{ success, users: T[], total, page, limit, total_pages }` | `unwrapLegacyList(res, 'users')` |
| **Bare object** | `POST /events`, `GET/PATCH /events/{id}`, approve/reject/assign | the event object itself with an embedded `success: true` field, **no `data` wrapper** | `stripSuccess(res)` |

Two more wire quirks the normalizers absorb:

- **Redundant inner `success`:** registration and attendance objects (single and inside
  paginated `data`) each carry their own `"success": true` field. Strip it; never read it.
- **Auth responses are bespoke:** `{ success, data: { user, accessToken, refreshToken } }`
  for signup/login; `{ success, data: { accessToken, refreshToken } }` for refresh.

Example api module (the pattern all of them follow):

```ts
// api/events.api.ts
export const listEvents = (p: EventListParams) =>
  client.get('/events', { params: { page: p.page, limit: p.limit, status: p.status,
    type: p.type, category: p.category, search: p.search } })   // NB: param is `type`, not `event_type`
    .then(r => unwrapLegacyList<EventListItem>(r.data, 'items'));

export const getEvent = (id: string) =>
  client.get(`/events/${id}`).then(r => stripSuccess<Event>(r.data));

export const approveEvent = (id: string, admin_comment?: string) =>
  client.patch(`/events/${id}/approve`, { admin_comment })
    .then(r => stripSuccess<Event>(r.data));
```

### Full endpoint inventory the frontend consumes

All paths under `VITE_API_BASE_URL` (= `/api/v1`). Guard column = backend enforcement;
the frontend mirrors it in routing/UI but the backend is authoritative.

| # | Method & path | Guard | Frontend use |
|---|---|---|---|
| 1 | `POST /auth/signup` | public | SignupPage. Body: `{name (2–120), email (@college.edu), password (8–100), role: 'student'\|'teacher'}` → 201 + user + tokens |
| 2 | `POST /auth/login` | public | LoginPage. 401 bad creds; **403 = account not active** (pending teacher banner) |
| 3 | `POST /auth/refresh` | public | interceptor only. Body `{refreshToken}`; **rotates** — old refresh token is blacklisted |
| 4 | `POST /auth/logout` | authed | Logout action. Body `{refreshToken}` |
| 5 | `GET /auth/me` | authed | Session bootstrap on app load |
| 6 | `GET /users/pending-teachers?page&limit` | admin | Admin Panel — approval queue |
| 7 | `PATCH /users/{id}/approve` | admin | Admin Panel row action |
| 8 | `PATCH /users/{id}/reject` | admin | Admin Panel row action |
| 9 | `GET /users/teachers?search&page&limit` | admin | AssignCoordinatorDialog (active teachers, name-sorted, searchable) |
| 10 | `GET /events?page&limit&status&type&category&search` | authed | Event lists everywhere. **Server scopes by role**: student→approved only; teacher→coordinated OR created; admin→all |
| 11 | `POST /events` | authed (service enforces) | Admin creates `in_college` (→ draft); Student creates `out_college` (→ pending). Teachers cannot create at all |
| 12 | `GET /events/{id}` | authed | EventDetail (full shape incl. `created_by`/`coordinator` objects) |
| 13 | `PATCH /events/{id}` | creator or admin | Edit form. Updatable: title, description, category, venue, start/end_date. **Not** type/status/max_registrations |
| 14 | `PATCH /events/{id}/approve` | admin or assigned coordinator (teacher) | Approve action. Optional `admin_comment` — **accepted but not persisted** (§12) |
| 15 | `PATCH /events/{id}/reject` | admin or coordinator | Reject dialog. `admin_comment` **required, min 1 char** |
| 16 | `PATCH /events/{id}/assign-coordinator` | ⚠️ any authed user (backend gap) | Admin UI only. Body `{coordinator_id}` — must be an **active teacher** |
| 17 | `POST /registrations` | student | JoinEventSheet. Body `{event_id, role_type}` → 201, status pending |
| 18 | `GET /registrations/my?status&page&limit` | student | Participation / Volunteering tabs (filter client-side by `role_type`, server-side by `status`) |
| 19 | `GET /registrations/event/{eventId}?status&page&limit` | teacher/admin (must be coordinator or admin) | Registrations sub-tab |
| 20 | `PATCH /registrations/{id}/accept` | coordinator/admin, pending only | Accept action (+ notification to student, server-side) |
| 21 | `PATCH /registrations/{id}/reject` | coordinator/admin, pending only | Reject action |
| 22 | `POST /attendance/bulk` | coordinator/admin | Save Attendance. Body `{eventId, date: 'YYYY-MM-DD', records: [{studentId, present}]}`, 1–100 records, upserts. Every student must hold an **accepted** registration, else 409 for the whole batch |
| 23 | `GET /attendance/event/{eventId}?date&page&limit` | coordinator/admin | Attendance sub-tab (prefill grid for a day) |
| 24 | `GET /attendance/my?eventId&status&page&limit` | any authed | Student "My Attendance" page |
| 25 | `GET /attendance/student/{studentId}?page&limit` | **admin only** | Admin drill-down (optional page) |
| 26 | `GET /notifications?page&limit&unread_only` | authed | NotificationsPage / bell dropdown |
| 27 | `GET /notifications/unread-count` | authed | Bell badge — polled |
| 28 | `PATCH /notifications/{id}/read` | owner | Mark-read on click |
| 29 | `PATCH /notifications/read-all` | authed | "Mark all read" |
| 30 | `GET /reports/dashboard` | teacher/admin | Teacher & Admin dashboards (aggregate counts) |
| 31 | `GET /health` | public | Optional connectivity indicator |

There is **no** single-mark attendance endpoint, **no** upload endpoint, **no**
`/health/ready`, and **no** student-scoped reports endpoint.

## 6. Error handling

One `toApiError()` in `api/errors.ts` converts every failure into:

```ts
interface ApiError {
  status: number;                 // HTTP status — the PRIMARY branch key
  code: string;                   // best-effort code, see below
  message: string;                // human-readable, safe to toast
  fieldErrors?: Record<string, string>;  // populated from 422 shapes
  retryAfter?: number;            // seconds, from 429 Retry-After header
}
```

It must understand **three distinct error body shapes**:

1. **App envelope** (custom exceptions, rate limiter, timeout):
   `{"success": false, "error": {"code", "message", "details?"}}` — codes:
   `NOT_FOUND` 404, `UNAUTHORIZED` 401, `FORBIDDEN` 403, `VALIDATION_ERROR` 422,
   `CONFLICT` 409, `RATE_LIMITED` 429, `REQUEST_TIMEOUT` 503, `INTERNAL_ERROR` 500.
2. **Same envelope but `code: "HTTP_ERROR"`** — legacy services (all of auth, teacher
   approve/reject) and the auth guards raise plain `HTTPException`, so e.g. a login
   failure is `{"error": {"code": "HTTP_ERROR", "message": "Invalid email or password"}}`
   with status 401. **Therefore: branch on `status`, never solely on `code`.**
3. **FastAPI default 422** for request-body validation (bad email/enum/missing field):
   `{"detail": [{loc, msg, type}]}` — no `success` key at all. Map `loc` → `fieldErrors`
   so RHF can surface them under the right inputs. (Client-side Zod should make these
   rare, but the handler must not crash on the shape.)

Global behaviors (axios interceptor + TanStack Query defaults):

- **401** on any non-auth call → attempt refresh once (see §7); if refresh fails →
  clear session → redirect `/login?next=…`.
- **403** → toast "You don't have permission" and, on route-level fetches, render the
  Forbidden page. Special case login 403 = "Account awaiting admin approval" banner.
- **409** → surface `message` inline in the initiating dialog/form (these are business
  rules: "Event has no coordinator assigned", "Already registered…", capacity full,
  "already approved", non-pending registration…). Never a generic toast — the message is
  the UX.
- **422** → field errors into the form.
- **429** → toast with countdown from `retryAfter`; TanStack Query `retry` config: never
  auto-retry 4xx, retry 5xx/network once. Note auth endpoints are limited to
  **20 req/min/IP** and everything else 100/min — polling intervals in §10 respect this.
- **503 REQUEST_TIMEOUT** (30s server cap) → toast "Server took too long, try again".

## 7. Auth architecture

### Token model (matches backend exactly)

- **Access token**: 15 min TTL, payload `{sub, role, type: 'access'}` — sent as
  `Authorization: Bearer <token>` on every request.
- **Refresh token**: 7 days, `{sub, type: 'refresh'}` — used only against
  `POST /auth/refresh`, which returns a **new pair and blacklists the old refresh token**
  (rotation).

### Storage & bootstrap

- Access token: **in-memory** (Zustand, non-persisted) — never in localStorage.
- Refresh token: `localStorage` (PDF explicitly allows localStorage; backend has no
  cookie support, so this is the only way to survive a reload).
- App boot: if a refresh token exists → call `/auth/refresh` → store new pair → call
  `/auth/me` → hydrate `auth.store` → render. Otherwise → `/login`. Show a full-page
  spinner during bootstrap so guarded routes never flash.

### Refresh rotation — the single-flight rule

Because refresh **rotates and blacklists**, two concurrent refresh calls with the same
token mean the second one 401s and nukes the session. The interceptor must serialize:

```
request → 401 → is a refresh already in flight?
  yes → await the shared promise, then retry with the new access token
  no  → start refresh, share its promise, swap tokens atomically, retry queued requests
refresh itself fails (401) → hard logout
```

This is the single most bug-prone piece of the frontend; it gets dedicated tests (MSW)
covering: parallel 401s, refresh failure, token swap mid-flight, logout during refresh.

### Session store (Zustand)

```ts
interface AuthState {
  user: User | null;
  accessToken: string | null;          // memory only
  status: 'booting' | 'authed' | 'guest';
  login(email, password): Promise<void>;
  signup(payload): Promise<void>;
  logout(): Promise<void>;             // POST /auth/logout with refreshToken, then clear
  // refresh handled inside api/client.ts, writes back via store setter
}
```

Role checks in the UI read `user.role` (hydrated from `/auth/me`), not the JWT — no JWT
parsing in the frontend at all.

### Route guards

- `<ProtectedRoute>` — `status === 'authed'` else redirect `/login?next=<path>`.
- `<RoleRoute allow={['admin']}>` — else redirect to the caller's own portal root
  (friendlier than a 403 page for nav mistakes; the Forbidden page is reserved for
  server-side 403s).
- After login: redirect by role → `student → /student`, `teacher → /teacher`,
  `admin → /admin` (honoring `?next=` when its role prefix matches).

## 8. Routing map

```
/                         → redirect by auth status/role
/login                    AuthLayout
/signup                   AuthLayout

/student                  PortalLayout(role=student)   — nav: Dashboard | Events | Participation | Volunteering
  /student                Dashboard
  /student/events         Browse events + "My Requests" segmented control + FAB "Raise Out-College Event"
  /student/events/:id     Event detail (+ Join sheet)
  /student/participation  Registrations where role_type=participant
  /student/volunteering   Registrations where role_type=volunteer
  /student/attendance     My attendance records
  /student/notifications  Notifications page

/teacher                  PortalLayout(role=teacher)   — nav: Dashboard | Events
  /teacher                Dashboard (reports + assigned-events table)
  /teacher/events         Assigned/created events, search + status filter
  /teacher/events/:id     Event detail — tabs: Overview | Registrations | Attendance
  /teacher/notifications  Notifications page

/admin                    PortalLayout(role=admin)     — nav: Dashboard | Events | Admin Panel
  /admin                  Dashboard (reports + platform stats)
  /admin/events           Full event table + Create Event
  /admin/events/:id       Event detail — Overview | Registrations | Attendance | Manage (approve/reject/assign)
  /admin/panel            Pending teacher approvals + active teacher directory
  /admin/notifications    Notifications page

/forbidden, *             system pages
```

The three portals share `PortalLayout` (left sidebar ≥`md`, bottom tab bar below — per
PDF §5.3/5.4/5.5) parameterized by a per-role nav config. The topbar holds the
NotificationBell, user name/role chip, and logout.

## 9. Design system

### Status colors (PDF §10 — the contract for every badge/chip/calendar dot)

| Token | Hex | Meaning |
|---|---|---|
| `status-approved-in` | `#2E6DA4` blue | Approved in_college event |
| `status-approved-out` | `#1A8A7A` teal | Approved out_college event |
| `status-pending` | `#F59E0B` amber | Pending (event, registration, teacher account) |
| `status-rejected` | `#DC2626` red | Rejected (any) |
| `status-accepted` | `#16A34A` green | Accepted registration / present |
| `status-draft` | `#6B7280` grey | Draft / inactive / absent |

Implement as Tailwind theme colors + one `<StatusBadge kind status>` component so every
list renders statuses identically (kind ∈ event | registration | attendance | user, since
"pending" means something different per entity but always renders amber).

### Core shared components

- `DataTable` — thin wrapper over shadcn Table: column defs, empty state, loading
  skeleton, integrated `Paginator` (drives `page`/`limit` query params; `limit` ≤ 100).
- `Paginator` — reads the normalized `Paginated<T>` meta; URL-synced (`?page=2`) so
  back/refresh preserve position.
- `ConfirmDialog` — every mutating row action (approve/reject/accept) confirms with the
  consequence spelled out ("Student will be notified").
- `StatCard` — dashboard tiles (label, count, icon, accent color).
- `EmptyState` — illustration + CTA (e.g. "No events yet — Raise an Out-College Event").
- `EventCard` — title, date range, type badge (blue/teal), category chip, status chip,
  `registration_count` ("12 registered"). Note: list items expose `created_by_name`
  (string) only; the full creator/coordinator objects require the detail fetch.
- `SearchInput` — 300 ms debounce → `search` query param.

## 10. Server-state design (TanStack Query)

### Query keys

```
['me']
['events', 'list', {page, limit, status, type, category, search}]
['events', 'detail', eventId]
['registrations', 'my', {page, limit, status}]
['registrations', 'event', eventId, {page, limit, status}]
['attendance', 'event', eventId, {date, page, limit}]
['attendance', 'my', {eventId, status, page, limit}]
['attendance', 'student', studentId, {page, limit}]
['notifications', 'list', {page, limit, unread_only}]
['notifications', 'unread-count']
['users', 'pending-teachers', {page, limit}]
['users', 'teachers', {search, page, limit}]
['reports', 'dashboard']
```

### Invalidation map (mutation → refetch)

| Mutation | Invalidate |
|---|---|
| create event | `['events','list']`, `['reports']` |
| update event | `['events','detail',id]`, `['events','list']` |
| approve/reject event | detail + list + `['reports']` (server also notifies creator) |
| assign coordinator | `['events','detail',id]` |
| register (join) | `['registrations','my']`, `['events','detail',id]`, list (registration_count) |
| accept/reject registration | `['registrations','event',eventId]`, `['reports']` |
| bulk attendance | `['attendance','event',eventId]`, `['reports']` |
| mark notification(s) read | `['notifications']` (both keys) |
| approve/reject teacher | `['users','pending-teachers']`, `['users','teachers']`, `['reports']` |

### Polling

- `['notifications','unread-count']`: `refetchInterval: 60_000`, plus
  `refetchOnWindowFocus`. One request/min is far below the 100/min general limit, and
  it doubles as the mechanism by which users "receive" accept/reject outcomes — there is
  no push channel.
- Everything else: `staleTime: 30_000`, no polling; mutations invalidate.

## 11. Pages & flows in detail

### 11.1 Auth

**LoginPage** — two-column AuthLayout (branding left, form right). Email + password
(Zod: email contains `@` + dotted domain; password non-empty). Submit → store.login().
- 401 → inline "Invalid email or password".
- **403 → amber banner: "Your account is pending Admin approval."** (backend returns 403
  "Account is not active" for pending/rejected — we show the pending wording per PDF; the
  message from the server is displayed as secondary text).
- Success → role redirect.

**SignupPage** — Full Name (2–120), College Email (Zod regex mirrors backend: must end
`@college.edu` — read the suffix from a frontend constant so it stays in one place),
Password (8–100) + Confirm, Role toggle (Student / Teacher).
- Teacher selected → persistent info note: "Your account will be active after Admin
  approval" (backend signs teachers up as `pending` and still returns tokens, but login
  thereafter 403s until approval — so after teacher signup we do **not** auto-enter the
  app: show success screen "Account created — awaiting approval" and route to /login).
- Student signup → tokens received → straight into `/student` (status is `active`
  immediately).
- 409 (email exists) → inline field error.

**Session expiry UX** — silent (interceptor). Only a failed refresh logs the user out,
with a toast "Session expired — please log in again".

### 11.2 Student portal

**Dashboard** (`/student`)
- Welcome header (name from store).
- Stat cards — computed client-side (no student reports endpoint):
  - *Active events joined* = `/registrations/my?status=accepted` → meta.total
  - *Pending approvals* = `/registrations/my?status=pending` → meta.total
  - *Volunteering* / *Participation* counts = client-side split of accepted rows by `role_type`
  (fetch `limit=100` once for the split; totals from the two status-filtered `meta.total`s).
- "Upcoming events" strip: `/events?status=approved&limit=10` sorted by `start_date`,
  horizontal scroll, color-coded type chips (blue/teal per PDF).

**Events** (`/student/events`) — segmented control **Browse | My Requests**
- **Browse**: card grid of `/events` (server already scopes students to `approved`).
  Filters: type (All / In-College / Out-College), category, search. Card → detail page.
- **My Requests**: the student's own out_college submissions. The list endpoint scopes
  students to approved-only, so a student cannot see their own pending event in the
  list — **the frontend keeps a local record**: after `POST /events` succeeds, store the
  returned event ids (`localStorage`, keyed by user id) and render My Requests by
  fetching each via `GET /events/{id}` (detail endpoint has no status scoping). Status
  chips: pending amber / approved teal / rejected red. *(Flagged in §12 as a backend
  improvement: a `created_by=me` filter would remove this workaround.)*
- **FAB "+ Raise Out-College Event"** → full-screen form (mobile) / dialog (desktop):
  title, description, venue ("organizer/location" per PDF maps to venue), start/end
  datetime, category. Zod mirrors backend: start ≥ today, end ≥ start, title 1–200,
  venue 1–300. Submit → `POST /events` with `event_type: 'out_college'` → lands as
  `pending` → success toast "Submitted for approval" → appears in My Requests.
  **No brochure upload — the backend has no upload endpoint** (§12); the form includes an
  optional "brochure link (URL)" only in the description text for now.

**EventDetail** (`/student/events/:id`)
- Header: title, type badge, status chip, date range, venue, coordinator name (or
  "Coordinator not yet assigned"), capacity line: `max_registrations === 0 ? 'Unlimited
  slots' : '<accepted>/<max> slots'` (accepted count not exposed on detail — show
  "Limited capacity: <max>" instead; the authoritative check is server-side on join).
- **Join button** → bottom sheet: pick role (Volunteer / Participant — offer only roles
  compatible with the event's `category`; `both` offers both), confirm → `POST
  /registrations`. Disabled states with reason text:
  - event not approved → hidden entirely
  - no coordinator assigned → "Registration opens once a coordinator is assigned"
    (pre-empts the 409)
  - already registered for that role (known from `/registrations/my` cache) → "Requested"
    chip instead of button; a `both`-category event still offers the other role.
  - 409 responses (capacity, duplicate, no coordinator) → inline message from server.

**Participation** (`/student/participation`) & **Volunteering** (`/student/volunteering`)
- Same component, parameterized by `role_type`. Data: `/registrations/my` (server
  filters by status; role split is client-side per page). Rows: event title (link),
  event dates, registered date, status badge (pending amber / accepted green / rejected
  red). Status filter tabs: All | Pending | Accepted | Rejected.
- ~~Upload Proof button~~ — **not built**: no backend support (§12).

**My Attendance** (`/student/attendance`)
- `/attendance/my`, filterable by event (dropdown fed from accepted registrations) and
  status. Rows: event, date, present/absent badge (green/grey). Simple summary line:
  "Present X of Y marked days" computed from the current filter's fetched pages.

**Notifications** (`/student/notifications` — same shared page in all portals)
- List from `/notifications`, unread rows highlighted; tap → `PATCH /{id}/read` +
  deep-link by `related_entity_type`: `event → /<role>/events/<id>`,
  `registration → participation/volunteering (student) or the event's registrations tab
  (teacher/admin)`, `user → /admin/panel` (admin only). "Mark all read" button.
- Bell in topbar: unread-count badge (polled), dropdown shows latest 5 + "View all".

### 11.3 Teacher portal

**Dashboard** (`/teacher`)
- Stat cards from `GET /reports/dashboard`: pending registrations
  (`registrations.by_status.pending`), events by status, attendance totals. *(Note: these
  are platform-wide aggregates, not per-teacher — render honest labels: "Platform
  pending approvals". Per-teacher numbers come from the events table below.)*
- "My events" table: `/events` (server scopes teachers to coordinated-or-created), with
  status chips and `registration_count`; row → EventDetail.

**Events** (`/teacher/events`)
- Same list with search + status filter + client-side date-range filter on the fetched
  page (backend has no date filter param).

**EventDetail** (`/teacher/events/:id`) — header + tabs **Overview | Registrations |
Attendance**
- **Overview**: full event info; if `status === 'pending'` and I am the coordinator →
  **Approve / Reject** buttons (reject dialog requires a comment — backend rejects an
  empty `admin_comment`). 409s ("already approved", "cannot approve a rejected event")
  surfaced inline.
- **Registrations tab**: `/registrations/event/{id}` table — student name, email,
  role_type chip, registered date, status badge, row actions **Accept / Reject** (only on
  `pending` rows; others show the final badge). Checkbox multi-select + bulk bar: "Accept
  (n) / Reject (n)" implemented as sequential PATCH calls with a progress indicator and
  per-row failure report (there is no bulk endpoint; sequential keeps us inside rate
  limits at realistic sizes). Status filter tabs; count chips per status.
- **Attendance tab**:
  - Day picker: chips `Day 1 … Day N` generated from `eventDays(start_date, end_date)`;
    selecting a day sets `date`.
  - Grid: roster = **accepted registrations** for the event
    (`/registrations/event/{id}?status=accepted`), merged with existing marks
    (`/attendance/event/{id}?date=`). Each student: toggle Present/Absent (default
    Absent = backend semantics of `present: false`).
  - "Mark all present" convenience toggle.
  - **Save** → `POST /attendance/bulk` `{eventId, date, records}` (≤100 records per call;
    chunk if the roster exceeds 100). Success toast with server `message`. 409 means
    someone in the batch lacks an accepted registration — refetch roster and retell.
  - `late` may appear in fetched records (enum exists) — render it amber; the toggle
    never produces it.

### 11.4 Admin portal

**Dashboard** (`/admin`)
- Platform stats from `/reports/dashboard`: Total Events, Active Students
  (`users.by_role.student` with by_status active where derivable — show role totals and a
  secondary status line), Pending Approvals (events pending + teachers pending +
  registrations pending as three small cards), Teachers count, notifications unread.
- Color-coded month calendar (PDF §5.5): events plotted on their date ranges — blue
  in_college, teal out_college, amber pending. Data: `/events?limit=100` (admin sees
  all); client-side placement. (Good enough for a single college's volume; paginate/lazy
  by month if it ever grows.)

**Events** (`/admin/events`)
- Full `DataTable` with filter bar: status (All/Draft/Pending/Approved/Rejected), type,
  category, search. Columns: title, type badge, category, status, dates,
  registration_count, creator name.
- **"+ Create Event"** → dialog: title, description, venue, category, start/end dates.
  `event_type` fixed to `in_college` (backend forbids admin creating out_college).
  Submit → event lands in **draft**.
- Row actions / detail **Manage** tab:
  - **Assign Coordinator** → dialog with searchable dropdown of `/users/teachers`
    (active only) → `PATCH /{id}/assign-coordinator`.
  - **Approve / Reject** with comment field (reject: required). Approve available from
    draft or pending. Surface the backend truth in the dialog: *comments on approval are
    not stored* — the UI labels the field "Comment (sent nowhere yet — see CONCERNS)"
    or simply omits the field on approve until §12.2 lands. Reject comment is required
    by the API but likewise not persisted; it still gates the action.
  - **Edit** (creator/admin): the `PATCH /events/{id}` fields only.
- Recommended admin ops flow (encode as inline hints): create → assign coordinator →
  approve. Registration is impossible until a coordinator exists, so the approve dialog
  warns when `coordinator === null`: "Students cannot register until a coordinator is
  assigned."

**EventDetail** (`/admin/events/:id`) — Overview | Registrations | Attendance | Manage.
Registrations/Attendance tabs are the same components as the teacher portal (admin
passes all backend authz checks).

**Admin Panel** (`/admin/panel`)
- **Pending Teacher Accounts**: `/users/pending-teachers` table — name, email, registered
  date, **Approve / Reject** buttons (ConfirmDialog; server creates the
  teacher_approved/rejected notification). 404/409 edge cases toast the server message.
- **Teacher Directory**: `/users/teachers` with search — reference list; also the pool
  shown by AssignCoordinatorDialog.

### 11.5 End-to-end lifecycle walkthroughs (what must demo cleanly)

**A. In-College event (admin-created):**
1. Admin: Events → Create (→ draft, grey chip)
2. Admin: Assign Coordinator (active teacher)
3. Admin (or coordinator): Approve (→ approved, blue) — creator gets `event_approved` notification
4. Student: Browse → EventDetail → Join as Volunteer/Participant (→ registration pending, amber)
5. Coordinator: EventDetail → Registrations → Accept (→ accepted, green) — student's bell badge increments within ≤60 s
6. Coordinator: Attendance → pick Day 2 → toggle present → Save (bulk upsert)
7. Student: My Attendance shows present (green) for that date

**B. Out-College event (student-raised):**
1. Student: Events → FAB → submit form (→ pending, amber; appears in My Requests)
2. Admin: Events (filter Pending) → assign coordinator if desired → Approve/Reject with comment — student receives `event_approved`/`event_rejected` notification
3. If approved (+ coordinator assigned): other students may register; lifecycle continues as A4–A7.
   *(Proof-of-attendance upload from the PDF is deferred — §12.)*

## 12. Backend gaps this plan must respect (and proposed backend work)

The frontend **must not** assume any of these exist today. Each is either designed
around (above) or listed here as a small backend follow-up for the team to decide on —
they follow the `/add-module` / migration conventions if picked up.

| # | Gap (verified in code) | Frontend accommodation | Suggested backend fix (optional, separate decision) |
|---|---|---|---|
| 1 | **No file uploads at all** — no brochure/proof endpoints, no `brochure_url`/`proof_url` columns, no S3 | Upload UI omitted from Raise-Event and Participation flows; PDF's "Out-College Proof Review" teacher sub-tab **not built** | New `uploads` capability: columns + endpoints (Supabase Storage is the natural fit) — a full module-pattern change |
| 2 | `admin_comment` accepted on approve/reject but **not persisted** (no column) | Reject dialog still requires a comment (API mandates it) but UI doesn't promise the student sees it; no "rejection reason" display anywhere | Migration adding `events.admin_comment`, include in `EventOut`, show on student's My Requests |
| 3 | `max_registrations` **cannot be set** via create/update (always 0 = unlimited) | Capacity UI reads it but never edits; create form has no capacity field | Add field to `EventCreate`/`EventUpdate` |
| 4 | Student event list scoped to `approved` → students can't list their own pending submissions | "My Requests" via locally-remembered ids + `GET /events/{id}` | Add `mine=true` (or include own `created_by` rows in student scope) to `GET /events` |
| 5 | `assign-coordinator` guarded only by `get_current_user` (known concern) | UI exposes it only in the admin portal — but this is cosmetic, not security | Add `require_admin` to the route |
| 6 | No per-teacher/per-student stats endpoint (`/reports/dashboard` is global, teacher/admin-only) | Teacher dashboard labels stats as platform-wide; student dashboard computes from own lists | Optional scoped reports later |
| 7 | Registration accepted-count not exposed on event detail | Capacity shown as "Limited: N" not "x/N" | Add `accepted_count` to `EventOut` |
| 8 | No bulk accept/reject registrations endpoint | Sequential PATCH with progress UI | Optional bulk endpoint |
| 9 | Draft in_college events have no "submit" transition | Admin approves straight from draft (approve endpoint doesn't require pending) | none needed |
| 10 | Pydantic body errors return FastAPI's default `{"detail": [...]}` 422 (not the app envelope) | `toApiError()` parses both shapes | Optional `RequestValidationError` handler for envelope consistency |

## 13. Testing strategy

- **Unit (Vitest)**: envelope normalizers (all 5 wire shapes incl. inner-`success`
  stripping), `toApiError()` (3 error shapes + Retry-After), `eventDays()`, Zod schemas
  (mirror backend limits: title 200, venue 300, password 8–100, email suffix).
- **Component (RTL + MSW)**: MSW handlers return **verbatim wire shapes** (snake_case,
  legacy events envelope, camelCase tokens) so any normalization regression fails tests.
  Cover per page: loading/empty/error states, role-gated action visibility, 409 inline
  messaging, form validation.
- **Auth integration (MSW)**: the refresh single-flight suite (§7) — parallel 401s,
  rotation, failed refresh → logout, bootstrap from stored refresh token.
- **Flow tests**: the two §11.5 walkthroughs as MSW-backed integration tests (stateful
  handlers).
- Later/optional: Playwright E2E against `docker compose --profile local-db up` +
  `scripts/seed.py` seeded users (`admin@college.edu`/`Admin@123`, etc.) — mirrors the
  backend's `e2e` marker philosophy: opt-in, not in the default suite.

## 14. Implementation phases (each phase = shippable, small conventional commits)

Commit style matches the repo: `feat(frontend/<area>): <what>`, one concern per commit.

**Phase 0 — Scaffold** (~half day)
Vite + TS + Tailwind + shadcn init, router skeleton, layouts, theme tokens (status
colors), `.env.example`, README section.

**Phase 1 — API foundation** (the load-bearing phase)
`client.ts` (interceptors + single-flight refresh), `envelopes.ts`, `errors.ts`,
`types/`, `auth.store.ts`, bootstrap flow, Login/Signup pages, ProtectedRoute/RoleRoute,
portal shells with nav. *Exit: login as seeded admin/teacher/student lands on the right
empty portal; token refresh proven by test.*

**Phase 2 — Events read + Student join**
Events api/hooks, Browse grid + filters + EventCard, EventDetail, JoinEventSheet,
Participation/Volunteering pages, `/registrations/my`. *Exit: lifecycle A steps 4 works
against seeded data.*

**Phase 3 — Teacher/Admin management**
Registrations-by-event table + accept/reject (+bulk bar), event approve/reject dialogs,
admin Create Event, AssignCoordinatorDialog, Admin Panel (pending teachers). *Exit:
lifecycles A and B demo end-to-end except attendance.*

**Phase 4 — Attendance**
Day picker + grid + bulk save + chunking, student My Attendance. *Exit: lifecycle A
complete.*

**Phase 5 — Notifications + Dashboards**
Bell + polling + list + deep links + mark-read; reports-backed teacher/admin dashboards;
student computed dashboard; admin calendar; Student "My Requests" (local-ids workaround).

**Phase 6 — Hardening & ship**
Error/empty/loading polish, 429/503 UX, responsive pass (bottom nav), a11y pass
(focus traps in dialogs, badge contrast), MSW test debt to green, `frontend` service in
docker-compose (nginx static + proxy), docs: update this file's status, README, and
`docs/codebase/` pointers.

Dependencies: 1 → 2 → {3, 4} → 5 → 6 (3 and 4 parallelizable).

---

*Written 2026-07-12 against backend commit `77b792c`. If backend contracts change
(especially §12 items landing), update §5/§11/§12 in the same PR.*

*Status 2026-07-13: implemented in `frontend/` — all phases (0–6) including the full §13
test suite (48 tests) and an axe-core a11y + responsive audit against a locally seeded
backend. Two deviations from this doc, both deliberate: status colors used for **text**
are darkened to meet WCAG AA contrast (the PDF §10 hexes remain, as `status-vivid`, for
non-text marks like calendar dots); filter-only tab rows are rendered as toggle-button
groups rather than ARIA tabs (no tab panels exist for them). During verification two
backend bugs were found and fixed: migration 0001 declared `events.coordinator_id`
NOT NULL (model says nullable — fresh-DB event creation 500ed), and the registration
list queries lazy-loaded `event`/`student` relationships the routers touch after the
session (MissingGreenlet 500 on `GET /registrations/my` and `/registrations/event/{id}`).*
