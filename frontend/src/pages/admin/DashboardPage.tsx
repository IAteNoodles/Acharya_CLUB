import { Bell, CalendarDays, GraduationCap, UsersRound } from 'lucide-react';
import { Link } from 'react-router-dom';
import { PageHeader } from '@/components/common/PageHeader';
import { StatCard } from '@/components/common/StatCard';
import { MonthCalendar } from '@/components/events/MonthCalendar';
import { Skeleton } from '@/components/ui/skeleton';
import { useEventsList } from '@/hooks/useEvents';
import { useDashboard } from '@/hooks/useReports';

export function DashboardPage() {
  const { data: stats } = useDashboard();
  const { data: allEvents, isPending: eventsPending } = useEventsList({ limit: 100 });

  const roleStatus = (role: string, status: string) =>
    stats ? (stats.users.by_role_status[role]?.[status] ?? 0) : '—';

  return (
    <div>
      <PageHeader title="Dashboard" description="Platform activity across the college." />

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Total events" value={stats?.events.total ?? '—'} icon={CalendarDays} />
        <StatCard
          label="Students"
          value={stats?.users.by_role.student ?? '—'}
          icon={GraduationCap}
          hint={`${roleStatus('student', 'active')} active`}
        />
        <StatCard
          label="Teachers"
          value={stats?.users.by_role.teacher ?? '—'}
          icon={UsersRound}
          hint={`${roleStatus('teacher', 'active')} active`}
        />
        <StatCard
          label="Unread notifications"
          value={stats?.notifications.unread ?? '—'}
          icon={Bell}
          hint="Across all users"
        />
      </div>

      <section aria-labelledby="pending-heading" className="mt-6">
        <h2 id="pending-heading" className="mb-3 text-lg font-semibold">
          Pending approvals
        </h2>
        <div className="grid gap-3 sm:grid-cols-3">
          <Link to="/admin/events?status=pending" className="rounded-md focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring">
            <StatCard
              label="Events"
              value={stats?.events.by_status.pending ?? '—'}
              hint="Review under Events"
              className="h-full transition-colors hover:border-ink/40"
            />
          </Link>
          <Link to="/admin/panel" className="rounded-md focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring">
            <StatCard
              label="Teacher accounts"
              value={roleStatus('teacher', 'pending')}
              hint="Review in the Admin Panel"
              className="h-full transition-colors hover:border-ink/40"
            />
          </Link>
          <StatCard
            label="Registrations"
            value={stats?.registrations.by_status.pending ?? '—'}
            hint="Reviewed per event by coordinators"
            className="h-full"
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
