import { CalendarDays } from 'lucide-react';
import { Link, useSearchParams } from 'react-router-dom';
import { DataTable, type Column } from '@/components/common/DataTable';
import { EmptyState } from '@/components/common/EmptyState';
import { PageHeader } from '@/components/common/PageHeader';
import { Paginator } from '@/components/common/Paginator';
import { SearchInput } from '@/components/common/SearchInput';
import { StatusBadge } from '@/components/common/StatusBadge';
import { CreateEventDialog } from '@/components/events/CreateEventDialog';
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
import type { EventCategory, EventStatus, EventType } from '@/types/enums';

const STATUSES: EventStatus[] = ['draft', 'pending', 'approved', 'rejected'];

export function EventsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const page = Number(searchParams.get('page')) || 1;
  const status = (searchParams.get('status') as EventStatus | null) ?? undefined;
  const type = (searchParams.get('type') as EventType | null) ?? undefined;
  const category = (searchParams.get('category') as EventCategory | null) ?? undefined;
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

  const { data, isPending } = useEventsList({
    page,
    status,
    type,
    category,
    search: search || undefined,
  });

  const columns: Column<EventListItem>[] = [
    {
      key: 'title',
      header: 'Event',
      cell: (event) => (
        <Link
          to={`/admin/events/${event.id}`}
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
      key: 'category',
      header: 'Category',
      cell: (event) => <span className="capitalize">{event.category}</span>,
    },
    {
      key: 'status',
      header: 'Status',
      cell: (event) => (
        <StatusBadge kind="event" status={event.status} eventType={event.event_type} />
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
      key: 'creator',
      header: 'Created by',
      cell: (event) => event.created_by_name ?? '—',
    },
  ];

  return (
    <div>
      <PageHeader
        title="Events"
        description="Every event on the platform, in any state."
        actions={<CreateEventDialog />}
      />
      <div className="mb-4 flex flex-col gap-2 lg:flex-row">
        <div className="lg:w-64">
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
          <SelectTrigger className="lg:w-36" aria-label="Filter by status">
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
        <Select
          value={type ?? 'all'}
          onValueChange={(value) => setParam('type', value === 'all' ? null : value)}
        >
          <SelectTrigger className="lg:w-36" aria-label="Filter by type">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All types</SelectItem>
            <SelectItem value="in_college">In-College</SelectItem>
            <SelectItem value="out_college">Out-College</SelectItem>
          </SelectContent>
        </Select>
        <Select
          value={category ?? 'all'}
          onValueChange={(value) => setParam('category', value === 'all' ? null : value)}
        >
          <SelectTrigger className="lg:w-40" aria-label="Filter by category">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All categories</SelectItem>
            <SelectItem value="participant">Participation</SelectItem>
            <SelectItem value="volunteer">Volunteering</SelectItem>
            <SelectItem value="both">Both</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <DataTable
        columns={columns}
        rows={data?.items ?? []}
        rowKey={(event) => event.id}
        loading={isPending}
        caption="All events"
        emptyState={
          <EmptyState
            icon={CalendarDays}
            title="No events match"
            description="Adjust the filters, or create an In-College event."
          />
        }
      />
      {data && <Paginator meta={data} onPageChange={(next) => setParam('page', String(next), false)} />}
    </div>
  );
}
