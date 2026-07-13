import type { AppNotification } from '@/types/domain';
import { client } from './client';
import { unwrapData, unwrapPaginated } from './envelopes';

export interface NotificationListParams {
  page?: number;
  limit?: number;
  unread_only?: boolean;
}

export const listNotifications = (params: NotificationListParams = {}) =>
  client
    .get('/notifications', { params })
    .then((r) => unwrapPaginated<AppNotification>(r.data));

export const getUnreadCount = () =>
  client.get('/notifications/unread-count').then((r) => unwrapData<{ count: number }>(r.data).count);

export const markNotificationRead = (id: string) =>
  client.patch(`/notifications/${id}/read`).then((r) => unwrapData<AppNotification>(r.data));

export const markAllNotificationsRead = () =>
  client.patch('/notifications/read-all').then((r) => unwrapData<{ count: number }>(r.data));
