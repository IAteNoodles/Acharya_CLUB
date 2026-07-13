import { CalendarDays, ClipboardCheck, Clock, UsersRound } from 'lucide-react';
import { Link } from 'react-router-dom';
import { DataTable, type Column } from '@/components/common/DataTable';
import { EmptyState } from '@/components/common/EmptyState';
import { PageHeader } from '@/components/common/PageHeader';
import { StatCard } from '@/components/common/StatCard';
import { StatusBadge } from '@/components/common/StatusBadge';
import { useEventsList } from '@/hooks/useEvents';
import { useDashboard } from '@/hooks/useReports';
import { formatDateRange } from '@/lib/format';
import { useAuthStore } from '@/stores/auth.store';
import type { EventListItem } from '@/types/domain';

export function DashboardPage() {
  const user = useAuthStore((s) => s.user);
  const { data: stats } = useDashboard();
  const { data: myEvents, isPending: eventsPending } = useEventsList({ limit: 10 });

  const columns: Column<EventListItem>[] = [
    {
      key: 'title',
      header: 'Event',
      cell: (event) => (
        <Link
          to={`/teacher/events/${event.id}`}
          className="font-medium underline-offset-4 hover:underline"
        >
          {event.title}
        </Link>
      ),
    },
    {
      key: 'dates',
      header: 'Dates',
      cell: (event) => formatDateRange(event.start_date, event.end_date),
    },
    {
      key: 'registrations',
      header: 'Registered',
      className: 'tabular-nums',
      cell: (event) => event.registration_count,
    },
    {
      key: 'status',
      header: 'Status',
      cell: (event) => (
        <StatusBadge kind="event" status={event.status} eventType={event.event_type} />
      ),
    },
  ];

  return (
    <div>
      <PageHeader
        title={`Welcome, ${user?.name?.split(' ')[0] ?? 'there'}`}
        description="Platform activity and the events you manage."
      />

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Pending registrations"
          value={stats?.registrations.by_status.pending ?? '—'}
          icon={Clock}
          hint="Platform-wide"
        />
        <StatCard
          label="Approved events"
          value={stats?.events.by_status.approved ?? '—'}
          icon={CalendarDays}
          hint="Platform-wide"
        />
        <StatCard
          label="Pending events"
          value={stats?.events.by_status.pending ?? '—'}
          icon={CalendarDays}
          hint="Platform-wide"
        />
        <StatCard
          label="Attendance records"
          value={stats?.attendance.total ?? '—'}
          icon={ClipboardCheck}
          hint="Platform-wide"
        />
      </div>

      <section aria-labelledby="my-events-heading" className="mt-8">
        <div className="mb-3 flex items-center justify-between">
          <h2 id="my-events-heading" className="text-lg font-semibold">
            My events
          </h2>
          <Link
            to="/teacher/events"
            className="text-sm font-medium underline-offset-4 hover:underline"
          >
            View all
          </Link>
        </div>
        <DataTable
          columns={columns}
          rows={myEvents?.items ?? []}
          rowKey={(event) => event.id}
          loading={eventsPending}
          caption="Events you coordinate or created"
          emptyState={
            <EmptyState
              icon={UsersRound}
              title="No events assigned to you yet"
              description="Events you coordinate or created appear here."
            />
          }
        />
      </section>
    </div>
  );
}
