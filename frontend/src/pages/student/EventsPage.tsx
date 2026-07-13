import { CalendarDays } from 'lucide-react';
import { useSearchParams } from 'react-router-dom';
import { EmptyState } from '@/components/common/EmptyState';
import { PageHeader } from '@/components/common/PageHeader';
import { Paginator } from '@/components/common/Paginator';
import { SearchInput } from '@/components/common/SearchInput';
import { StatusBadge } from '@/components/common/StatusBadge';
import { EventCard } from '@/components/events/EventCard';
import { RaiseEventDialog } from '@/components/events/RaiseEventDialog';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useEventsList, useMyRequestEvents } from '@/hooks/useEvents';
import { formatDateRange } from '@/lib/format';
import { myEventRequestIds } from '@/lib/myRequests';
import { useAuthStore } from '@/stores/auth.store';
import type { EventCategory, EventType } from '@/types/enums';

function BrowseTab() {
  const [searchParams, setSearchParams] = useSearchParams();
  const page = Number(searchParams.get('page')) || 1;
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

  const { data, isPending } = useEventsList({ page, type, category, search: search || undefined });

  return (
    <div>
      <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-center">
        <div className="sm:w-64">
          <SearchInput
            value={search}
            onDebouncedChange={(value) => setParam('q', value || null)}
            placeholder="Search events…"
            label="Search events"
          />
        </div>
        <Select
          value={type ?? 'all'}
          onValueChange={(value) => setParam('type', value === 'all' ? null : value)}
        >
          <SelectTrigger className="sm:w-40" aria-label="Filter by type">
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
          <SelectTrigger className="sm:w-44" aria-label="Filter by category">
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

      {isPending ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }, (_, i) => (
            <Skeleton key={i} className="h-36 rounded-md" />
          ))}
        </div>
      ) : !data || data.items.length === 0 ? (
        <EmptyState
          icon={CalendarDays}
          title="No events match"
          description="Try clearing the filters, or raise an Out-College event yourself."
        />
      ) : (
        <>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {data.items.map((event) => (
              <EventCard key={event.id} event={event} href={`/student/events/${event.id}`} />
            ))}
          </div>
          <Paginator meta={data} onPageChange={(next) => setParam('page', String(next), false)} />
        </>
      )}
    </div>
  );
}

function MyRequestsTab() {
  const user = useAuthStore((s) => s.user);
  const ids = user ? myEventRequestIds(user.id) : [];
  const queries = useMyRequestEvents(ids);
  const events = queries
    .map((query) => query.data)
    .filter((event): event is NonNullable<typeof event> => !!event);
  const loading = queries.some((query) => query.isPending);

  if (ids.length === 0) {
    return (
      <EmptyState
        icon={CalendarDays}
        title="No requests yet"
        description="Raise an Out-College event and it will show up here with its approval status."
      />
    );
  }

  return (
    <div className="overflow-hidden rounded-md border bg-card">
      <ul className="divide-y">
        {loading && events.length === 0 && (
          <li className="p-4">
            <Skeleton className="h-5 w-1/2" />
          </li>
        )}
        {events.map((event) => (
          <li key={event.id} className="flex items-center justify-between gap-3 p-4">
            <div className="min-w-0">
              <p className="truncate font-medium">{event.title}</p>
              <p className="text-sm text-muted-foreground">
                {formatDateRange(event.start_date, event.end_date)}
                {event.venue ? ` · ${event.venue}` : ''}
              </p>
            </div>
            <StatusBadge kind="event" status={event.status} eventType={event.event_type} />
          </li>
        ))}
      </ul>
    </div>
  );
}

export function EventsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const tab = searchParams.get('tab') === 'requests' ? 'requests' : 'browse';

  return (
    <div>
      <PageHeader
        title="Events"
        description="Browse approved events or track your own submissions."
        actions={<RaiseEventDialog />}
      />
      <Tabs
        value={tab}
        onValueChange={(value) =>
          setSearchParams((prev) => {
            const next = new URLSearchParams(prev);
            if (value === 'requests') next.set('tab', 'requests');
            else next.delete('tab');
            next.delete('page');
            return next;
          })
        }
      >
        <TabsList className="mb-4">
          <TabsTrigger value="browse">Browse</TabsTrigger>
          <TabsTrigger value="requests">My Requests</TabsTrigger>
        </TabsList>
        <TabsContent value="browse">
          <BrowseTab />
        </TabsContent>
        <TabsContent value="requests">
          <MyRequestsTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}
