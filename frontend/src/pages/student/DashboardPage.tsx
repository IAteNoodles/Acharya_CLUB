import { CalendarDays, CircleCheck, Clock, HeartHandshake, Ticket } from 'lucide-react';
import { Link } from 'react-router-dom';
import { EmptyState } from '@/components/common/EmptyState';
import { PageHeader } from '@/components/common/PageHeader';
import { StatCard } from '@/components/common/StatCard';
import { EventCard } from '@/components/events/EventCard';
import { Skeleton } from '@/components/ui/skeleton';
import { useEventsList } from '@/hooks/useEvents';
import { useMyRegistrations } from '@/hooks/useRegistrations';
import { useAuthStore } from '@/stores/auth.store';

export function DashboardPage() {
  const user = useAuthStore((s) => s.user);
  const { data: acceptedData } = useMyRegistrations({ status: 'accepted', limit: 100 });
  const { data: pendingData } = useMyRegistrations({ status: 'pending', limit: 1 });
  const { data: upcoming, isPending: upcomingPending } = useEventsList({
    status: 'approved',
    limit: 10,
  });

  const accepted = acceptedData?.items ?? [];
  const volunteering = accepted.filter((reg) => reg.role_type === 'volunteer').length;
  const participation = accepted.filter((reg) => reg.role_type === 'participant').length;

  const upcomingEvents = [...(upcoming?.items ?? [])].sort((a, b) =>
    a.start_date.localeCompare(b.start_date),
  );

  return (
    <div>
      <PageHeader
        title={`Welcome, ${user?.name?.split(' ')[0] ?? 'there'}`}
        description="Your events at a glance."
      />

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Events joined"
          value={acceptedData?.total ?? '—'}
          icon={CircleCheck}
          hint="Accepted registrations"
        />
        <StatCard
          label="Pending approvals"
          value={pendingData?.total ?? '—'}
          icon={Clock}
          hint="Awaiting coordinator review"
        />
        <StatCard label="Participation" value={participation} icon={Ticket} hint="Accepted as participant" />
        <StatCard label="Volunteering" value={volunteering} icon={HeartHandshake} hint="Accepted as volunteer" />
      </div>

      <section aria-labelledby="upcoming-heading" className="mt-8">
        <div className="mb-3 flex items-center justify-between">
          <h2 id="upcoming-heading" className="text-lg font-semibold">
            Upcoming events
          </h2>
          <Link
            to="/student/events"
            className="text-sm font-medium underline-offset-4 hover:underline"
          >
            Browse all
          </Link>
        </div>
        {upcomingPending ? (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 3 }, (_, i) => (
              <Skeleton key={i} className="h-36 rounded-md" />
            ))}
          </div>
        ) : upcomingEvents.length === 0 ? (
          <EmptyState
            icon={CalendarDays}
            title="No approved events right now"
            description="Check back soon, or raise an Out-College event yourself."
          />
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {upcomingEvents.map((event) => (
              <EventCard key={event.id} event={event} href={`/student/events/${event.id}`} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
