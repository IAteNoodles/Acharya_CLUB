import type { Paginated, User } from '@/types/domain';
import { client } from './client';
import { unwrapData, unwrapLegacyList } from './envelopes';

export const listPendingTeachers = (params: { page?: number; limit?: number } = {}) =>
  client
    .get('/users/pending-teachers', { params })
    .then((r) => unwrapLegacyList<User>(r.data, 'users'));

export const listTeachers = (
  params: { search?: string; page?: number; limit?: number } = {},
): Promise<Paginated<User>> =>
  client
    .get('/users/teachers', { params: { ...params, search: params.search || undefined } })
    .then((r) => unwrapLegacyList<User>(r.data, 'users'));

export const approveTeacher = (id: string) =>
  client.patch(`/users/${id}/approve`).then((r) => unwrapData<User>(r.data));

export const rejectTeacher = (id: string) =>
  client.patch(`/users/${id}/reject`).then((r) => unwrapData<User>(r.data));
