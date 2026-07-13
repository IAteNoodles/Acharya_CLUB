import { ArrowLeft, CalendarDays, MapPin, UserRound, UsersRound } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import { isApiError } from '@/api/errors';
import { EmptyState } from '@/components/common/EmptyState';
import { StatusBadge, statusLabel } from '@/components/common/StatusBadge';
import { JoinEventSheet } from '@/components/registrations/JoinEventSheet';
import { Skeleton } from '@/components/ui/skeleton';
import { useEvent } from '@/hooks/useEvents';
import { useMyRegistrations } from '@/hooks/useRegistrations';
import { formatDateRange } from '@/lib/format';
import type { RegistrationRole } from '@/types/enums';

export function EventDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data: event, isPending, error } = useEvent(id);
  const { data: myRegistrations } = useMyRegistrations({ limit: 100 });

  if (isPending) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-8 w-2/3" />
        <Skeleton className="h-5 w-1/3" />
        <Skeleton className="h-40 rounded-md" />
      </div>
    );
  }

  if (error || !event) {
    return (
      <EmptyState
        title={isApiError(error) && error.status === 404 ? 'Event not found' : 'Could not load event'}
        description="It may have been removed, or the link is wrong."
        action={
          <Link to="/student/events" className="text-sm font-medium underline underline-offset-4">
            Back to events
          </Link>
        }
      />
    );
  }

  const mine = (myRegistrations?.items ?? []).filter((reg) => reg.event_id === event.id);
  const takenRoles = mine.map((reg) => reg.role_type);
  const offeredRoles: RegistrationRole[] =
    event.category === 'both' ? ['participant', 'volunteer'] : [event.category];
  const openRoles = offeredRoles.filter((role) => !takenRoles.includes(role));

  return (
    <div className="mx-auto max-w-3xl">
      <Link
        to="/student/events"
        className="mb-4 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft aria-hidden="true" className="h-4 w-4" />
        Back to events
      </Link>

      <div className="rounded-md border bg-card p-5 sm:p-6">
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge kind="event-type" status={event.event_type} />
          <StatusBadge kind="event" status={event.status} eventType={event.event_type} />
        </div>
        <h1 className="mt-3 text-2xl font-semibold">{event.title}</h1>

        <dl className="mt-4 grid gap-2 text-sm sm:grid-cols-2">
          <div className="flex items-center gap-2">
            <CalendarDays aria-hidden="true" className="h-4 w-4 text-muted-foreground" />
            <dt className="sr-only">Dates</dt>
            <dd>{formatDateRange(event.start_date, event.end_date)}</dd>
          </div>
          <div className="flex items-center gap-2">
            <MapPin aria-hidden="true" className="h-4 w-4 text-muted-foreground" />
            <dt className="sr-only">Venue</dt>
            <dd>{event.venue ?? 'Venue to be announced'}</dd>
          </div>
          <div className="flex items-center gap-2">
            <UserRound aria-hidden="true" className="h-4 w-4 text-muted-foreground" />
            <dt className="sr-only">Coordinator</dt>
            <dd>
              {event.coordinator ? event.coordinator.name : 'Coordinator not yet assigned'}
            </dd>
          </div>
          <div className="flex items-center gap-2">
            <UsersRound aria-hidden="true" className="h-4 w-4 text-muted-foreground" />
            <dt className="sr-only">Capacity</dt>
            <dd>
              {event.max_registrations === 0
                ? 'Unlimited slots'
                : `Limited capacity: ${event.max_registrations}`}
            </dd>
          </div>
        </dl>

        {event.description && (
          <p className="mt-4 whitespace-pre-wrap text-sm text-muted-foreground">
            {event.description}
          </p>
        )}

        {event.status === 'approved' && (
          <div className="mt-6 border-t pt-4">
            {mine.length > 0 && (
              <ul className="mb-3 space-y-1.5">
                {mine.map((reg) => (
                  <li key={reg.id} className="flex items-center gap-2 text-sm">
                    <span className="capitalize">{reg.role_type}</span>
                    <StatusBadge kind="registration" status={reg.status} />
                    {reg.status === 'pending' && (
                      <span className="text-muted-foreground">Requested — awaiting review</span>
                    )}
                  </li>
                ))}
              </ul>
            )}
            {!event.coordinator ? (
              <p className="text-sm text-muted-foreground">
                Registration opens once a coordinator is assigned.
              </p>
            ) : openRoles.length > 0 ? (
              <JoinEventSheet event={event} takenRoles={takenRoles} />
            ) : (
              <p className="text-sm text-muted-foreground">
                You've requested every available role for this event
                {mine.length === 1 ? ` (${statusLabel(mine[0].status).toLowerCase()})` : ''}.
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
