import { CalendarDays, UsersRound } from 'lucide-react';
import { Link } from 'react-router-dom';
import { StatusBadge } from '@/components/common/StatusBadge';
import { formatDateRange } from '@/lib/format';
import type { EventListItem } from '@/types/domain';

export function EventCard({ event, href }: { event: EventListItem; href: string }) {
  return (
    <Link
      to={href}
      className="group flex flex-col gap-2 rounded-md border bg-card p-4 transition-colors hover:border-ink/40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
    >
      <div className="flex items-start justify-between gap-2">
        <StatusBadge kind="event-type" status={event.event_type} />
        <StatusBadge kind="event" status={event.status} eventType={event.event_type} />
      </div>
      <h3 className="font-display text-base font-semibold leading-snug group-hover:underline group-hover:underline-offset-4">
        {event.title}
      </h3>
      <div className="mt-auto space-y-1 text-sm text-muted-foreground">
        <p className="flex items-center gap-1.5">
          <CalendarDays aria-hidden="true" className="h-3.5 w-3.5" />
          {formatDateRange(event.start_date, event.end_date)}
        </p>
        <p className="flex items-center gap-1.5 tabular-nums">
          <UsersRound aria-hidden="true" className="h-3.5 w-3.5" />
          {event.registration_count} registered
          <span>· {event.category}</span>
        </p>
        {event.created_by_name && (
          <p className="truncate text-xs text-muted-foreground">By {event.created_by_name}</p>
        )}
      </div>
    </Link>
  );
}
