import { formatDistanceToNow, parseISO } from 'date-fns';
import { BellOff, CheckCheck } from 'lucide-react';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { EmptyState } from '@/components/common/EmptyState';
import { PageHeader } from '@/components/common/PageHeader';
import { Paginator } from '@/components/common/Paginator';
import { notificationHref } from '@/components/notifications/notificationLink';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Switch } from '@/components/ui/switch';
import {
  useMarkAllNotificationsRead,
  useMarkNotificationRead,
  useNotifications,
  useUnreadCount,
} from '@/hooks/useNotifications';
import { cn } from '@/lib/utils';
import { useAuthStore } from '@/stores/auth.store';
import type { AppNotification } from '@/types/domain';

export function NotificationsPage() {
  const user = useAuthStore((s) => s.user);
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [unreadOnly, setUnreadOnly] = useState(false);

  const { data, isPending } = useNotifications({ page, unread_only: unreadOnly || undefined });
  const { data: unread = 0 } = useUnreadCount();
  const markRead = useMarkNotificationRead();
  const markAll = useMarkAllNotificationsRead();

  const open = (notification: AppNotification) => {
    if (!notification.is_read) markRead.mutate(notification.id);
    if (user) navigate(notificationHref(notification, user.role));
  };

  const markAllRead = async () => {
    const result = await markAll.mutateAsync();
    toast.success(
      result.count > 0 ? `Marked ${result.count} notifications as read.` : 'Nothing unread.',
    );
  };

  return (
    <div className="mx-auto max-w-2xl">
      <PageHeader
        title="Notifications"
        description={unread > 0 ? `${unread} unread` : 'You’re all caught up.'}
        actions={
          <Button variant="outline" size="sm" onClick={markAllRead} disabled={markAll.isPending}>
            <CheckCheck aria-hidden="true" className="h-4 w-4" />
            Mark all read
          </Button>
        }
      />

      <div className="mb-4 flex items-center gap-2">
        <Switch id="unread-only" checked={unreadOnly} onCheckedChange={(checked) => { setUnreadOnly(checked === true); setPage(1); }} />
        <label htmlFor="unread-only" className="text-sm">
          Unread only
        </label>
      </div>

      {isPending ? (
        <div className="space-y-2">
          {Array.from({ length: 4 }, (_, i) => (
            <Skeleton key={i} className="h-16 rounded-md" />
          ))}
        </div>
      ) : !data || data.items.length === 0 ? (
        <EmptyState
          icon={BellOff}
          title={unreadOnly ? 'Nothing unread' : 'No notifications yet'}
          description="Updates about your events, requests, and account land here."
        />
      ) : (
        <>
          <ul className="space-y-2">
            {data.items.map((notification) => (
              <li key={notification.id}>
                <button
                  type="button"
                  onClick={() => open(notification)}
                  className={cn(
                    'w-full rounded-md border bg-card p-3.5 text-left transition-colors hover:bg-secondary/50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring',
                    !notification.is_read && 'border-l-[3px] border-l-ink',
                  )}
                >
                  <div className="flex items-baseline justify-between gap-2">
                    <p className={cn('text-sm', !notification.is_read && 'font-semibold')}>
                      {notification.title}
                    </p>
                    <time
                      dateTime={notification.created_at}
                      className="shrink-0 text-xs text-muted-foreground"
                    >
                      {formatDistanceToNow(parseISO(notification.created_at), { addSuffix: true })}
                    </time>
                  </div>
                  <p className="mt-0.5 text-sm text-muted-foreground">{notification.message}</p>
                </button>
              </li>
            ))}
          </ul>
          <Paginator meta={data} onPageChange={setPage} />
        </>
      )}
    </div>
  );
}
