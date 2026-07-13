import { formatDistanceToNow, parseISO } from 'date-fns';
import { Bell } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Button } from '@/components/ui/button';
import {
  useMarkNotificationRead,
  useNotifications,
  useUnreadCount,
} from '@/hooks/useNotifications';
import { cn } from '@/lib/utils';
import type { AppNotification } from '@/types/domain';
import type { Role } from '@/types/enums';
import { notificationHref } from './notificationLink';

export function NotificationBell({ role }: { role: Role }) {
  const navigate = useNavigate();
  const { data: unread = 0 } = useUnreadCount();
  const { data: latest } = useNotifications({ page: 1, limit: 5 });
  const markRead = useMarkNotificationRead();

  const open = (notification: AppNotification) => {
    if (!notification.is_read) markRead.mutate(notification.id);
    navigate(notificationHref(notification, role));
  };

  const badge = unread > 99 ? '99+' : String(unread);

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          aria-label={unread > 0 ? `Notifications, ${unread} unread` : 'Notifications'}
          className="relative"
        >
          <Bell aria-hidden="true" className="h-4 w-4" />
          {unread > 0 && (
            <span
              aria-hidden="true"
              className="absolute -right-0.5 -top-0.5 grid min-w-4 place-items-center rounded-full bg-status-rejected px-1 text-[10px] font-bold leading-4 text-white"
            >
              {badge}
            </span>
          )}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-80">
        <DropdownMenuLabel>Notifications</DropdownMenuLabel>
        <DropdownMenuSeparator />
        {!latest || latest.items.length === 0 ? (
          <p className="px-2 py-6 text-center text-sm text-muted-foreground">
            Nothing yet. Updates about your events and requests appear here.
          </p>
        ) : (
          latest.items.map((notification) => (
            <DropdownMenuItem
              key={notification.id}
              onSelect={() => open(notification)}
              className="flex flex-col items-start gap-0.5 py-2"
            >
              <span className={cn('text-sm', !notification.is_read && 'font-semibold')}>
                {notification.title}
              </span>
              <span className="line-clamp-2 text-xs text-muted-foreground">
                {notification.message}
              </span>
              <span className="text-[11px] text-muted-foreground">
                {formatDistanceToNow(parseISO(notification.created_at), { addSuffix: true })}
              </span>
            </DropdownMenuItem>
          ))
        )}
        <DropdownMenuSeparator />
        <DropdownMenuItem onSelect={() => navigate(`/${role}/notifications`)}>
          View all notifications
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
