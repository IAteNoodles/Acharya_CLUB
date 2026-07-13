import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  acceptRegistration,
  listEventRegistrations,
  listMyRegistrations,
  register,
  rejectRegistration,
  type RegistrationListParams,
} from '@/api/registrations.api';
import type { RegistrationRole } from '@/types/enums';

export function useMyRegistrations(params: RegistrationListParams = {}) {
  return useQuery({
    queryKey: ['registrations', 'my', params],
    queryFn: () => listMyRegistrations(params),
  });
}

export function useEventRegistrations(
  eventId: string | undefined,
  params: RegistrationListParams = {},
) {
  return useQuery({
    queryKey: ['registrations', 'event', eventId, params],
    queryFn: () => listEventRegistrations(eventId!, params),
    enabled: !!eventId,
  });
}

export function useRegister(eventId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (role_type: RegistrationRole) => register(eventId, role_type),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['registrations', 'my'] });
      queryClient.invalidateQueries({ queryKey: ['events', 'detail', eventId] });
      queryClient.invalidateQueries({ queryKey: ['events', 'list'] });
    },
  });
}

export function useAcceptRegistration(eventId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: acceptRegistration,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['registrations', 'event', eventId] });
      queryClient.invalidateQueries({ queryKey: ['reports'] });
    },
  });
}

export function useRejectRegistration(eventId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: rejectRegistration,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['registrations', 'event', eventId] });
      queryClient.invalidateQueries({ queryKey: ['reports'] });
    },
  });
}
