import { ATTENDANCE_CHUNK_SIZE } from '@/lib/constants';
import type { AttendanceRecord, Paginated } from '@/types/domain';
import type { AttendanceStatus } from '@/types/enums';
import { client } from './client';
import { unwrapData, unwrapPaginated } from './envelopes';

export interface BulkMark {
  studentId: string;
  present: boolean;
}

export interface BulkResult {
  count: number;
  message: string;
}

export const markBulkAttendance = async (
  eventId: string,
  date: string,
  records: BulkMark[],
): Promise<BulkResult> => {
  const results: BulkResult[] = [];
  for (let i = 0; i < records.length; i += ATTENDANCE_CHUNK_SIZE) {
    const chunk = records.slice(i, i + ATTENDANCE_CHUNK_SIZE);
    const res = await client.post('/attendance/bulk', { eventId, date, records: chunk });
    results.push(unwrapData<BulkResult>(res.data));
  }
  return {
    count: results.reduce((sum, r) => sum + r.count, 0),
    message: results.at(-1)?.message ?? 'Attendance saved',
  };
};

export const listEventAttendance = (
  eventId: string,
  params: { date?: string; page?: number; limit?: number } = {},
): Promise<Paginated<AttendanceRecord>> =>
  client
    .get(`/attendance/event/${eventId}`, { params })
    .then((r) => unwrapPaginated<AttendanceRecord>(r.data));

export const listMyAttendance = (
  params: { eventId?: string; status?: AttendanceStatus; page?: number; limit?: number } = {},
): Promise<Paginated<AttendanceRecord>> =>
  client
    .get('/attendance/my', {
      params: {
        eventId: params.eventId,
        status: params.status,
        page: params.page,
        limit: params.limit,
      },
    })
    .then((r) => unwrapPaginated<AttendanceRecord>(r.data));
