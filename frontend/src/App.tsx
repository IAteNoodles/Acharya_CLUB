import { QueryClientProvider } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { RouterProvider } from 'react-router-dom';
import { queryClient } from '@/api/queryClient';
import { FullPageSpinner } from '@/components/common/FullPageSpinner';
import { Toaster } from '@/components/ui/sonner';
import { router } from '@/router';
import { useAuthStore } from '@/stores/auth.store';

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
