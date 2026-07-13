import type { AppNotification } from '@/types/domain';
import type { Role } from '@/types/enums';

export function notificationHref(notification: AppNotification, role: Role): string {
  const { related_entity_type, related_entity_id, type } = notification;
  if (related_entity_type === 'event' && related_entity_id) {
    return `/${role}/events/${related_entity_id}`;
  }
  if (related_entity_type === 'registration') {
    if (role === 'student') {
      return type === 'registration_accepted' || type === 'registration_rejected'
        ? '/student/participation'
        : '/student/events';
    }
    return `/${role}/events`;
  }
  if (related_entity_type === 'user' && role === 'admin') {
    return '/admin/panel';
  }
  return `/${role}`;
}
