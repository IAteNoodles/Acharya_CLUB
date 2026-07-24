import { useMutation, useQueries, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  approveEvent,
  assignCoordinator,
  createEvent,
  getEvent,
  listEvents,
  rejectEvent,
  updateEvent,
  type EventCreateInput,
  type EventListParams,
  type EventUpdateInput,
} from '@/api/events.api';
import type { Event } from '@/types/domain';

export function useEventsList(params: EventListParams = {}) {
  return useQuery({
    queryKey: ['events', 'list', params],
    queryFn: () => listEvents(params),
    refetchOnMount: 'always',
  });
}

export function useEvent(id: string | undefined) {
  return useQuery({
    queryKey: ['events', 'detail', id],
    queryFn: () => getEvent(id!),
    enabled: !!id,
  });
}

export function useMyRequestEvents(ids: string[]) {
  return useQueries({
    queries: ids.map((id) => ({
      queryKey: ['events', 'detail', id],
      queryFn: () => getEvent(id),
      retry: false,
    })),
  });
}

export function useCreateEvent() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: EventCreateInput) => createEvent(input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['events', 'list'] });
      queryClient.invalidateQueries({ queryKey: ['reports'] });
    },
  });
}

export function useUpdateEvent(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: EventUpdateInput) => updateEvent(id, input),
    onSuccess: (event: Event) => {
      queryClient.setQueryData(['events', 'detail', id], event);
      queryClient.invalidateQueries({ queryKey: ['events', 'list'] });
    },
  });
}

export function useApproveEvent(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (admin_comment?: string) => approveEvent(id, admin_comment),
    onSuccess: (event: Event) => {
      queryClient.setQueryData(['events', 'detail', id], event);
      queryClient.invalidateQueries({ queryKey: ['events', 'list'] });
      queryClient.invalidateQueries({ queryKey: ['reports'] });
    },
  });
}

export function useRejectEvent(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (admin_comment: string) => rejectEvent(id, admin_comment),
    onSuccess: (event: Event) => {
      queryClient.setQueryData(['events', 'detail', id], event);
      queryClient.invalidateQueries({ queryKey: ['events', 'list'] });
      queryClient.invalidateQueries({ queryKey: ['reports'] });
    },
  });
}

export function useAssignCoordinator(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (coordinator_id: string) => assignCoordinator(id, coordinator_id),
    onSuccess: (event: Event) => {
      queryClient.setQueryData(['events', 'detail', id], event);
      queryClient.invalidateQueries({ queryKey: ['events', 'list'] });
    },
  });
}
