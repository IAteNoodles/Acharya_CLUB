import { QueryCache, QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { RouterProvider } from 'react-router-dom';
import { toast } from 'sonner';
import { isApiError } from '@/api/errors';
import { FullPageSpinner } from '@/components/common/FullPageSpinner';
import { Toaster } from '@/components/ui/sonner';
import { router } from '@/router';
import { useAuthStore } from '@/stores/auth.store';

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

const queryClient = new QueryClient({
  queryCache: new QueryCache({
    onError: toastGlobalError,
  }),
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: shouldRetry,
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: false,
    },
  },
});

export default function App() {
  const bootstrap = useAuthStore((s) => s.bootstrap);
  const [booted, setBooted] = useState(false);

  useEffect(() => {
    bootstrap().finally(() => setBooted(true));
  }, [bootstrap]);

  return (
    <QueryClientProvider client={queryClient}>
      {booted ? <RouterProvider router={router} /> : <FullPageSpinner label="Signing you in" />}
      <Toaster position="top-center" closeButton />
    </QueryClientProvider>
  );
}
