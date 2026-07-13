import { CalendarDays } from 'lucide-react';
import { Link, useSearchParams } from 'react-router-dom';
import { DataTable, type Column } from '@/components/common/DataTable';
import { EmptyState } from '@/components/common/EmptyState';
import { PageHeader } from '@/components/common/PageHeader';
import { Paginator } from '@/components/common/Paginator';
import { SearchInput } from '@/components/common/SearchInput';
import { StatusBadge } from '@/components/common/StatusBadge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useEventsList } from '@/hooks/useEvents';
import { formatDateRange } from '@/lib/format';
import type { EventListItem } from '@/types/domain';
import type { EventStatus } from '@/types/enums';

const STATUSES: EventStatus[] = ['draft', 'pending', 'approved', 'rejected'];

export function EventsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const page = Number(searchParams.get('page')) || 1;
  const status = (searchParams.get('status') as EventStatus | null) ?? undefined;
  const search = searchParams.get('q') ?? '';

  const setParam = (key: string, value: string | null, resetPage = true) => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      if (value) next.set(key, value);
      else next.delete(key);
      if (resetPage) next.delete('page');
      return next;
    });
  };

  const { data, isPending } = useEventsList({ page, status, search: search || undefined });

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
      key: 'type',
      header: 'Type',
      cell: (event) => <StatusBadge kind="event-type" status={event.event_type} />,
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
        title="Events"
        description="Events you coordinate or created."
      />
      <div className="mb-4 flex flex-col gap-2 sm:flex-row">
        <div className="sm:w-64">
          <SearchInput
            value={search}
            onDebouncedChange={(value) => setParam('q', value || null)}
            placeholder="Search events…"
            label="Search events"
          />
        </div>
        <Select
          value={status ?? 'all'}
          onValueChange={(value) => setParam('status', value === 'all' ? null : value)}
        >
          <SelectTrigger className="sm:w-40" aria-label="Filter by status">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            {STATUSES.map((value) => (
              <SelectItem key={value} value={value} className="capitalize">
                {value}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <DataTable
        columns={columns}
        rows={data?.items ?? []}
        rowKey={(event) => event.id}
        loading={isPending}
        caption="Your events"
        emptyState={
          <EmptyState
            icon={CalendarDays}
            title="No events assigned to you yet"
            description="Events you coordinate or created appear here once an admin assigns you."
          />
        }
      />
      {data && <Paginator meta={data} onPageChange={(next) => setParam('page', String(next), false)} />}
    </div>
  );
}
