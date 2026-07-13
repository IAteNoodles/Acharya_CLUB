import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { ROLE_HOME } from '@/lib/constants';
import { useAuthStore } from '@/stores/auth.store';

export function NotFoundPage() {
  const user = useAuthStore((s) => s.user);
  const home = user ? ROLE_HOME[user.role] : '/login';
  return (
    <main className="grid min-h-screen place-items-center p-6">
      <div className="text-center">
        <p className="font-display text-6xl font-bold text-muted-foreground/40">404</p>
        <h1 className="mt-2 text-xl font-semibold">Page not found</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          The page you are looking for doesn't exist or has moved.
        </p>
        <Button asChild className="mt-6">
          <Link to={home}>Go to your portal</Link>
        </Button>
      </div>
    </main>
  );
}
