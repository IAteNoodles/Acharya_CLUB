import { Navigate, Outlet } from 'react-router-dom';
import { ROLE_HOME } from '@/lib/constants';
import { useAuthStore } from '@/stores/auth.store';
import type { Role } from '@/types/enums';

export function RoleRoute({ allow }: { allow: Role[] }) {
  const user = useAuthStore((s) => s.user);
  if (!user) return null;
  if (!allow.includes(user.role)) {
    return <Navigate to={ROLE_HOME[user.role] ?? '/login'} replace />;
  }
  return <Outlet />;
}
