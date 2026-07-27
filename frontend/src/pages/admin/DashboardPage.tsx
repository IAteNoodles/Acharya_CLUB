import { Bell, CalendarDays, CheckCircle2, GraduationCap, UsersRound } from 'lucide-react';
import { Link } from 'react-router-dom';
import { CompositionBar } from '@/components/common/CompositionBar';
import { PageHeader } from '@/components/common/PageHeader';
import { StatCard } from '@/components/common/StatCard';
import { MonthCalendar } from '@/components/events/MonthCalendar';
import { Skeleton } from '@/components/ui/skeleton';
import { useEventsList } from '@/hooks/useEvents';
import { useDashboard } from '@/hooks/useReports';

const LINK_CARD =
  'rounded-md focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring';

export function DashboardPage() {
  const { data: stats } = useDashboard();
  const { data: allEvents, isPending: eventsPending } = useEventsList({ limit: 100 });

  const count = (n: number | undefined) => (stats ? (n ?? 0) : '—');
  const roleStatus = (role: string, status: string) =>
    count(stats?.users.by_role_status[role]?.[status]);

  const eventsWaiting = count(stats?.events.by_status.pending);
  const teachersWaiting = roleStatus('teacher', 'pending');
  const registrationsWaiting = count(stats?.registrations.by_status.pending);
  const allClear =
    !!stats && eventsWaiting === 0 && teachersWaiting === 0 && registrationsWaiting === 0;

  return (
    <div>
      <PageHeader title="Dashboard" description="What needs approving, and who is on the platform." />

      <section aria-labelledby="waiting-heading">
        <h2 id="waiting-heading" className="mb-3 text-lg font-semibold">
          Needs a decision
        </h2>
        {allClear ? (
          <div className="flex items-center gap-2 rounded-md border bg-card p-4 text-sm text-muted-foreground">
            <CheckCircle2 aria-hidden="true" className="h-4 w-4 text-status-accepted" />
            Nothing needs a decision right now.
          </div>
        ) : (
          <div className="grid gap-3 sm:grid-cols-3">
            <Link to="/admin/events?status=pending" className={LINK_CARD}>
              <StatCard
                label="Events to review"
                value={eventsWaiting}
                hint="Approve or reject under Events"
                className="h-full transition-colors hover:border-ink/40"
              />
            </Link>
            <Link to="/admin/panel" className={LINK_CARD}>
              <StatCard
                label="Teachers to approve"
                value={teachersWaiting}
                hint="Approve or reject in the Admin Panel"
                className="h-full transition-colors hover:border-ink/40"
              />
            </Link>
            <StatCard
              label="Registrations to review"
              value={registrationsWaiting}
              hint="Each event's coordinator reviews these"
              className="h-full"
            />
          </div>
        )}
      </section>

      <section aria-labelledby="platform-heading" className="mt-6">
        <h2 id="platform-heading" className="mb-3 text-lg font-semibold">
          Platform
        </h2>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard
            label="Events"
            value={count(stats?.events.total)}
            icon={CalendarDays}
            footer={<CompositionBar kind="event" counts={stats?.events.by_status ?? {}} />}
          />
          <StatCard
            label="Student accounts"
            value={count(stats?.users.by_role.student)}
            icon={GraduationCap}
            footer={
              <CompositionBar kind="user" counts={stats?.users.by_role_status.student ?? {}} />
            }
          />
          <StatCard
            label="Teacher accounts"
            value={count(stats?.users.by_role.teacher)}
            icon={UsersRound}
            footer={
              <CompositionBar kind="user" counts={stats?.users.by_role_status.teacher ?? {}} />
            }
          />
          <StatCard
            label="Unread notifications"
            value={count(stats?.notifications.unread)}
            icon={Bell}
            hint="Everyone's, not just yours"
          />
        </div>
      </section>

      <section aria-labelledby="calendar-heading" className="mt-6">
        <h2 id="calendar-heading" className="mb-3 text-lg font-semibold">
          Event calendar
        </h2>
        {eventsPending ? (
          <Skeleton className="h-96 rounded-md" />
        ) : (
          <MonthCalendar events={allEvents?.items ?? []} />
        )}
      </section>
    </div>
  );
}
