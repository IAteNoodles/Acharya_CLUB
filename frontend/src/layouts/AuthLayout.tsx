import { Outlet } from 'react-router-dom';

export function AuthLayout() {
  return (
    <div className="grid min-h-screen lg:grid-cols-[5fr_4fr]">
      <aside className="hidden flex-col justify-between bg-ink p-10 text-paper lg:flex">
        <div className="flex items-center gap-3">
          <span
            aria-hidden="true"
            className="grid h-10 w-10 place-items-center rounded-md border-2 border-paper/30 font-display text-sm font-bold"
          >
            AC
          </span>
          <span className="font-display text-lg font-semibold tracking-tight">AcharyaEngage</span>
        </div>
        <div>
          <h1 className="max-w-md font-display text-4xl font-bold leading-tight">
            Every event, from proposal to attendance register.
          </h1>
          <p className="mt-4 max-w-md text-paper/70">
            Raise events, assign coordinators, approve registrations, and keep the attendance
            ledger — all in one place for students, teachers, and administrators.
          </p>
        </div>
        <p className="text-sm text-paper/50">College Event Management System</p>
      </aside>
      <main className="flex items-center justify-center p-6 sm:p-10">
        <div className="w-full max-w-sm">
          <div className="mb-8 flex items-center gap-2 lg:hidden">
            <span
              aria-hidden="true"
              className="grid h-8 w-8 place-items-center rounded-md bg-ink font-display text-xs font-bold text-paper"
            >
              AC
            </span>
            <span className="font-display font-semibold">AcharyaEngage</span>
          </div>
          <Outlet />
        </div>
      </main>
    </div>
  );
}
