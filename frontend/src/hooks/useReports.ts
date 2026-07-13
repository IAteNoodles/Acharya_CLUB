import { useQuery } from '@tanstack/react-query';
import { getDashboard } from '@/api/reports.api';

export function useDashboard() {
  return useQuery({
    queryKey: ['reports', 'dashboard'],
    queryFn: getDashboard,
  });
}
