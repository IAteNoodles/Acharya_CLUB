import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { approveTeacher, listPendingTeachers, listTeachers, rejectTeacher } from '@/api/users.api';

export function usePendingTeachers(params: { page?: number; limit?: number } = {}) {
  return useQuery({
    queryKey: ['users', 'pending-teachers', params],
    queryFn: () => listPendingTeachers(params),
  });
}

export function useTeachers(params: { search?: string; page?: number; limit?: number } = {}) {
  return useQuery({
    queryKey: ['users', 'teachers', params],
    queryFn: () => listTeachers(params),
  });
}

function useTeacherAction(action: typeof approveTeacher) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: action,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users', 'pending-teachers'] });
      queryClient.invalidateQueries({ queryKey: ['users', 'teachers'] });
      queryClient.invalidateQueries({ queryKey: ['reports'] });
    },
  });
}

export const useApproveTeacher = () => useTeacherAction(approveTeacher);
export const useRejectTeacher = () => useTeacherAction(rejectTeacher);
