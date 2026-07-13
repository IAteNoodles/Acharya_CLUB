import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { ROLE_HOME } from '@/lib/constants';
import { useAuthStore } from '@/stores/auth.store';

export function ForbiddenPage() {
  const user = useAuthStore((s) => s.user);
  const home = user ? ROLE_HOME[user.role] : '/login';
  return (
    <main className="grid min-h-screen place-items-center p-6">
      <div className="text-center">
        <p className="font-display text-6xl font-bold text-muted-foreground/40">403</p>
        <h1 className="mt-2 text-xl font-semibold">You don't have permission to view this</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          If you think you should have access, contact an administrator.
        </p>
        <Button asChild className="mt-6">
          <Link to={home}>Go to your portal</Link>
        </Button>
      </div>
    </main>
  );
}
