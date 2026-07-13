import type { DashboardStats } from '@/types/domain';
import { client } from './client';
import { unwrapData } from './envelopes';

export const getDashboard = () =>
  client.get('/reports/dashboard').then((r) => unwrapData<DashboardStats>(r.data));
