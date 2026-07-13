import type { Paginated, Registration } from '@/types/domain';
import type { RegistrationRole, RegistrationStatus } from '@/types/enums';
import { client } from './client';
import { unwrapData, unwrapPaginated } from './envelopes';

export interface RegistrationListParams {
  page?: number;
  limit?: number;
  status?: RegistrationStatus;
}

export const register = (event_id: string, role_type: RegistrationRole) =>
  client.post('/registrations', { event_id, role_type }).then((r) => unwrapData<Registration>(r.data));

export const listMyRegistrations = (
  params: RegistrationListParams = {},
): Promise<Paginated<Registration>> =>
  client.get('/registrations/my', { params }).then((r) => unwrapPaginated<Registration>(r.data));

export const listEventRegistrations = (
  eventId: string,
  params: RegistrationListParams = {},
): Promise<Paginated<Registration>> =>
  client
    .get(`/registrations/event/${eventId}`, { params })
    .then((r) => unwrapPaginated<Registration>(r.data));

export const acceptRegistration = (id: string) =>
  client.patch(`/registrations/${id}/accept`).then((r) => unwrapData<Registration>(r.data));

export const rejectRegistration = (id: string) =>
  client.patch(`/registrations/${id}/reject`).then((r) => unwrapData<Registration>(r.data));
