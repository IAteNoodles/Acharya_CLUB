import { QueryCache, QueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { isApiError } from '@/api/errors';
import { STALE_TIME_MS } from '@/lib/constants';

function shouldRetry(failureCount: number, error: unknown) {
  if (failureCount >= 1) return false;
  if (isApiError(error)) return error.status === 0 || error.status >= 500;
  return true;
}

function toastGlobalError(error: unknown) {
  if (!isApiError(error)) return;
  if (error.status === 429) {
    toast.error(
      error.retryAfter
        ? `Too many requests — try again in ${error.retryAfter}s.`
        : 'Too many requests — slow down a moment.',
    );
  } else if (error.status === 503) {
    toast.error('Server took too long, try again.');
  } else if (error.status === 403) {
    toast.error("You don't have permission to do that.");
  } else if (error.status >= 500) {
    toast.error('Something went wrong on the server. Try again.');
  }
}

export const queryClient = new QueryClient({
  queryCache: new QueryCache({
    onError: toastGlobalError,
  }),
  defaultOptions: {
    queries: {
      staleTime: STALE_TIME_MS,
      retry: shouldRetry,
      refetchOnWindowFocus: true,
    },
    mutations: {
      retry: false,
    },
  },
});
