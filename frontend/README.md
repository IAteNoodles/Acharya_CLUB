# AcharyaEngage — Frontend

React SPA for the College Event Management System. Implements the plan in
[`docs/frontend-architecture.md`](../docs/frontend-architecture.md) — read that first;
this file covers only how to run and work on the app.

## Stack

React 18 · Vite · TypeScript · Tailwind CSS + shadcn/ui · React Router v6 ·
TanStack Query v5 · Zustand (session only) · React Hook Form + Zod · Axios ·
Vitest + Testing Library + MSW.

## Run

```bash
npm install
cp .env.example .env        # VITE_API_BASE_URL=http://localhost:8000/api/v1
npm run dev                 # http://localhost:5173
```

The backend must be running at `VITE_API_BASE_URL` (see `backend/README.md`).
Seed credentials for local demo: `admin@college.edu`/`Admin@123`,
`rajesh.kumar@college.edu`/`Teacher@123`, `priya.singh@college.edu`/`Student@123`.

```bash
npm test                    # vitest run — unit + MSW component/integration suites
npm run build               # tsc -b && vite build → dist/
```

## Layering rule

Pages/components never import axios or see wire envelopes. They call hooks
(`src/hooks/*`); hooks call `src/api/*`; only `src/api/` knows the backend's three
envelope styles, camelCase token/attendance quirks, and error shapes
(`envelopes.ts`, `errors.ts`, `client.ts`).

Auth: access token in memory, refresh token in localStorage, single-flight rotating
refresh in `api/client.ts` (tested in `api/refresh.integration.test.ts`).

## Design system

"Registrar's ledger": monochrome ink chrome (`ink`/`paper`/`rule` tokens); saturation is
reserved for status. `status.*` tokens are contrast-safe (AA on white and on the 8% tint
badges) and drive all text/badges via `<StatusBadge>`; `status-vivid.*` are the PDF §10
hexes for non-text marks (calendar dots). Type: Public Sans (UI) + Archivo (display),
self-hosted via Fontsource.

## Accessibility

Verified with axe-core (WCAG 2.0/2.1 A+AA) across every page at desktop and 390px mobile
widths, plus a keyboard/focus and contrast pass: skip link, visible focus rings, labeled
icon buttons, no `aria-controls` without a panel, `prefers-reduced-motion` respected.
Keep new UI to those standards.

## Docker

`frontend/Dockerfile` builds the Vite bundle (with `VITE_API_BASE_URL=/api/v1`) and
serves it from nginx, which also proxies `/api/v1` to the `backend` service — the SPA
and API stay same-origin, so no CORS and no baked-in host. `nginx.conf` adds the SPA
fallback (`try_files … /index.html`) and immutable caching for hashed assets. Run the
whole stack from the repo root: `docker compose up --build` → http://localhost:3000.
