import { Link, useParams } from 'react-router-dom';
import { isApiError } from '@/api/errors';
import { EmptyState } from '@/components/common/EmptyState';
import { ManageEventDetail } from '@/components/events/ManageEventDetail';
import { Skeleton } from '@/components/ui/skeleton';
import { useEvent } from '@/hooks/useEvents';

export function EventDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data: event, isPending, error } = useEvent(id);

  if (isPending) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-8 w-2/3" />
        <Skeleton className="h-64 rounded-md" />
      </div>
    );
  }

  if (error || !event) {
    return (
      <EmptyState
        title={isApiError(error) && error.status === 404 ? 'Event not found' : 'Could not load event'}
        description="It may have been removed, or the link is wrong."
        action={
          <Link to="/admin/events" className="text-sm font-medium underline underline-offset-4">
            Back to events
          </Link>
        }
      />
    );
  }

  return <ManageEventDetail event={event} role="admin" backHref="/admin/events" />;
}
