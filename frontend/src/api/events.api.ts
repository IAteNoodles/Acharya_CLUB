import type { Event, EventListItem, Paginated } from '@/types/domain';
import type { EventCategory, EventStatus, EventType } from '@/types/enums';
import { client } from './client';
import { stripSuccess, unwrapLegacyList } from './envelopes';

export interface EventListParams {
  page?: number;
  limit?: number;
  status?: EventStatus;
  type?: EventType;
  category?: EventCategory;
  search?: string;
}

export interface EventCreateInput {
  title: string;
  description?: string | null;
  event_type: EventType;
  category: EventCategory;
  venue: string;
  start_date: string;
  end_date: string;
}

export type EventUpdateInput = Partial<
  Pick<EventCreateInput, 'title' | 'description' | 'category' | 'venue' | 'start_date' | 'end_date'>
>;

export const listEvents = (params: EventListParams = {}): Promise<Paginated<EventListItem>> =>
  client
    .get('/events', {
      params: {
        page: params.page,
        limit: params.limit,
        status: params.status,
        type: params.type,
        category: params.category,
        search: params.search || undefined,
      },
    })
    .then((r) => unwrapLegacyList<EventListItem>(r.data, 'items'));

export const getEvent = (id: string) =>
  client.get(`/events/${id}`).then((r) => stripSuccess<Event>(r.data));

export const createEvent = (input: EventCreateInput) =>
  client.post('/events', input).then((r) => stripSuccess<Event>(r.data));

export const updateEvent = (id: string, input: EventUpdateInput) =>
  client.patch(`/events/${id}`, input).then((r) => stripSuccess<Event>(r.data));

export const approveEvent = (id: string, admin_comment?: string) =>
  client
    .patch(`/events/${id}/approve`, { admin_comment: admin_comment || undefined })
    .then((r) => stripSuccess<Event>(r.data));

export const rejectEvent = (id: string, admin_comment: string) =>
  client
    .patch(`/events/${id}/reject`, { admin_comment })
    .then((r) => stripSuccess<Event>(r.data));

export const assignCoordinator = (id: string, coordinator_id: string) =>
  client
    .patch(`/events/${id}/assign-coordinator`, { coordinator_id })
    .then((r) => stripSuccess<Event>(r.data));
