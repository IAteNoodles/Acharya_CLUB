import { ArrowLeft, CalendarDays, MapPin, UserRound, UsersRound } from 'lucide-react';
import { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { AttendanceTab } from '@/components/attendance/AttendanceTab';
import { StatusBadge } from '@/components/common/StatusBadge';
import {
  ApproveEventDialog,
  RejectEventDialog,
} from '@/components/events/ApproveRejectDialogs';
import { AssignCoordinatorDialog } from '@/components/events/AssignCoordinatorDialog';
import { EditEventDialog } from '@/components/events/EditEventDialog';
import { EventRegistrationsTable } from '@/components/registrations/EventRegistrationsTable';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { formatDateRange, formatDateTime } from '@/lib/format';
import { useAuthStore } from '@/stores/auth.store';
import type { Event } from '@/types/domain';

function OverviewTab({ event, role }: { event: Event; role: 'teacher' | 'admin' }) {
  const user = useAuthStore((s) => s.user);
  const [approveOpen, setApproveOpen] = useState(false);
  const [rejectOpen, setRejectOpen] = useState(false);
  const isCoordinator = !!user && event.coordinator?.id === user.id;
  const canDecide =
    role === 'admin'
      ? event.status === 'draft' || event.status === 'pending'
      : isCoordinator && event.status === 'pending';

  return (
    <div className="rounded-md border bg-card p-5">
      <dl className="grid gap-2 text-sm sm:grid-cols-2">
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
          <dd>{event.coordinator ? event.coordinator.name : 'Coordinator not yet assigned'}</dd>
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
        <p className="mt-4 whitespace-pre-wrap text-sm text-muted-foreground">{event.description}</p>
      )}

      <div className="mt-4 border-t pt-3 text-xs text-muted-foreground">
        <p>
          Created by {event.created_by?.name ?? 'unknown'} · {formatDateTime(event.created_at)}
        </p>
      </div>

      {canDecide && (
        <div className="mt-4 flex gap-2 border-t pt-4">
          <Button onClick={() => setApproveOpen(true)}>Approve</Button>
          <Button variant="outline" className="text-status-rejected hover:text-status-rejected" onClick={() => setRejectOpen(true)}>
            Reject
          </Button>
        </div>
      )}

      <ApproveEventDialog event={event} open={approveOpen} onOpenChange={setApproveOpen} />
      <RejectEventDialog event={event} open={rejectOpen} onOpenChange={setRejectOpen} />
    </div>
  );
}

function ManageTab({ event }: { event: Event }) {
  const [assignOpen, setAssignOpen] = useState(false);
  const [approveOpen, setApproveOpen] = useState(false);
  const [rejectOpen, setRejectOpen] = useState(false);
  const decided = event.status === 'approved' || event.status === 'rejected';

  return (
    <div className="space-y-4">
      <section className="rounded-md border bg-card p-5">
        <h2 className="text-sm font-semibold">Coordinator</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          {event.coordinator
            ? `${event.coordinator.name} (${event.coordinator.email})`
            : 'Not assigned. Students cannot register until a coordinator is assigned.'}
        </p>
        <Button variant="outline" className="mt-3" onClick={() => setAssignOpen(true)}>
          {event.coordinator ? 'Change coordinator' : 'Assign coordinator'}
        </Button>
      </section>

      <section className="rounded-md border bg-card p-5">
        <h2 className="text-sm font-semibold">Decision</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          {decided
            ? `This event is ${event.status}.`
            : 'Recommended flow: create → assign coordinator → approve.'}
        </p>
        {!decided && (
          <div className="mt-3 flex gap-2">
            <Button onClick={() => setApproveOpen(true)}>Approve</Button>
            <Button
              variant="outline"
              className="text-status-rejected hover:text-status-rejected"
              onClick={() => setRejectOpen(true)}
            >
              Reject
            </Button>
          </div>
        )}
      </section>

      <section className="rounded-md border bg-card p-5">
        <h2 className="text-sm font-semibold">Details</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Title, description, venue, dates, and category.
        </p>
        <div className="mt-3">
          <EditEventDialog event={event} />
        </div>
      </section>

      <AssignCoordinatorDialog event={event} open={assignOpen} onOpenChange={setAssignOpen} />
      <ApproveEventDialog event={event} open={approveOpen} onOpenChange={setApproveOpen} />
      <RejectEventDialog event={event} open={rejectOpen} onOpenChange={setRejectOpen} />
    </div>
  );
}

export function ManageEventDetail({
  event,
  role,
  backHref,
}: {
  event: Event;
  role: 'teacher' | 'admin';
  backHref: string;
}) {
  const [searchParams, setSearchParams] = useSearchParams();
  const tabs = role === 'admin' ? ['overview', 'registrations', 'attendance', 'manage'] : ['overview', 'registrations', 'attendance'];
  const tabParam = searchParams.get('tab');
  const tab = tabs.includes(tabParam ?? '') ? (tabParam as string) : 'overview';

  return (
    <div>
      <Link
        to={backHref}
        className="mb-4 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft aria-hidden="true" className="h-4 w-4" />
        Back to events
      </Link>

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <StatusBadge kind="event-type" status={event.event_type} />
        <StatusBadge kind="event" status={event.status} eventType={event.event_type} />
      </div>
      <h1 className="mb-4 text-2xl font-semibold">{event.title}</h1>

      <Tabs
        value={tab}
        onValueChange={(value) =>
          setSearchParams((prev) => {
            const next = new URLSearchParams(prev);
            if (value === 'overview') next.delete('tab');
            else next.set('tab', value);
            return next;
          })
        }
      >
        <TabsList className="mb-4 max-w-full overflow-x-auto">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="registrations">Registrations</TabsTrigger>
          <TabsTrigger value="attendance">Attendance</TabsTrigger>
          {role === 'admin' && <TabsTrigger value="manage">Manage</TabsTrigger>}
        </TabsList>
        <TabsContent value="overview">
          <OverviewTab event={event} role={role} />
        </TabsContent>
        <TabsContent value="registrations">
          <EventRegistrationsTable eventId={event.id} />
        </TabsContent>
        <TabsContent value="attendance">
          <AttendanceTab event={event} />
        </TabsContent>
        {role === 'admin' && (
          <TabsContent value="manage">
            <ManageTab event={event} />
          </TabsContent>
        )}
      </Tabs>
    </div>
  );
}
