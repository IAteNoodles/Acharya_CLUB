import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  listEventAttendance,
  listMyAttendance,
  markBulkAttendance,
  type BulkMark,
} from '@/api/attendance.api';
import type { AttendanceStatus } from '@/types/enums';

export function useEventAttendance(
  eventId: string | undefined,
  params: { date?: string; page?: number; limit?: number } = {},
) {
  return useQuery({
    queryKey: ['attendance', 'event', eventId, params],
    queryFn: () => listEventAttendance(eventId!, params),
    enabled: !!eventId,
  });
}

export function useMyAttendance(
  params: { eventId?: string; status?: AttendanceStatus; page?: number; limit?: number } = {},
) {
  return useQuery({
    queryKey: ['attendance', 'my', params],
    queryFn: () => listMyAttendance(params),
  });
}

export function useMarkBulkAttendance(eventId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ date, records }: { date: string; records: BulkMark[] }) =>
      markBulkAttendance(eventId, date, records),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['attendance', 'event', eventId] });
      queryClient.invalidateQueries({ queryKey: ['reports'] });
    },
  });
}
