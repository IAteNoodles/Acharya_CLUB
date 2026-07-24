import type { LucideIcon } from 'lucide-react';
import {
  Bell,
  CalendarDays,
  ClipboardCheck,
  HeartHandshake,
  KeyRound,
  LayoutDashboard,
  LogOut,
  Ticket,
  UserRound,
  UsersRound,
} from 'lucide-react';
import { useState } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { ChangePasswordDialog } from '@/components/auth/ChangePasswordDialog';
import { NotificationBell } from '@/components/notifications/NotificationBell';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { cn } from '@/lib/utils';
import { useAuthStore } from '@/stores/auth.store';
import type { Role } from '@/types/enums';

interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  end?: boolean;
}

const NAV: Record<Role, NavItem[]> = {
  student: [
    { to: '/student', label: 'Dashboard', icon: LayoutDashboard, end: true },
    { to: '/student/events', label: 'Events', icon: CalendarDays },
    { to: '/student/participation', label: 'Participation', icon: Ticket },
    { to: '/student/volunteering', label: 'Volunteering', icon: HeartHandshake },
    { to: '/student/attendance', label: 'Attendance', icon: ClipboardCheck },
  ],
  teacher: [
    { to: '/teacher', label: 'Dashboard', icon: LayoutDashboard, end: true },
    { to: '/teacher/events', label: 'Events', icon: CalendarDays },
  ],
  admin: [
    { to: '/admin', label: 'Dashboard', icon: LayoutDashboard, end: true },
    { to: '/admin/events', label: 'Events', icon: CalendarDays },
    { to: '/admin/panel', label: 'Admin Panel', icon: UsersRound },
  ],
};

export function PortalLayout({ role }: { role: Role }) {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const navigate = useNavigate();
  const items = NAV[role];
  const [passwordOpen, setPasswordOpen] = useState(false);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <div className="min-h-screen md:grid md:grid-cols-[220px_1fr]">
      <ChangePasswordDialog open={passwordOpen} onOpenChange={setPasswordOpen} />
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded-md focus:bg-ink focus:px-3 focus:py-2 focus:text-sm focus:text-paper"
      >
        Skip to main content
      </a>

      <aside className="hidden bg-ink text-paper md:flex md:flex-col">
        <div className="flex items-center gap-2.5 px-5 py-5">
          <span
            aria-hidden="true"
            className="grid h-9 w-9 shrink-0 place-items-center rounded-md border-2 border-paper/30 font-display text-xs font-bold"
          >
            AC
          </span>
          <div className="leading-tight">
            <p className="font-display text-sm font-semibold">Acharya CLUB</p>
            <p className="text-[11px] uppercase tracking-[0.12em] text-paper/70">{role} portal</p>
          </div>
        </div>
        <nav aria-label="Primary" className="mt-2 flex-1 space-y-0.5 px-3">
          {items.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-2.5 rounded-md px-2.5 py-2 text-sm text-paper/70 transition-colors hover:bg-paper/10 hover:text-paper focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-paper',
                  isActive && 'bg-paper/15 font-medium text-paper',
                )
              }
            >
              <item.icon aria-hidden="true" className="h-4 w-4 shrink-0" />
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-paper/15 p-3">
          <p className="truncate px-2 text-sm font-medium">{user?.name}</p>
          <p className="truncate px-2 text-xs text-paper/70">{user?.email}</p>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleLogout}
            className="mt-2 w-full justify-start gap-2 text-paper/70 hover:bg-paper/10 hover:text-paper"
          >
            <LogOut aria-hidden="true" className="h-4 w-4" />
            Log out
          </Button>
        </div>
      </aside>

      <div className="flex min-w-0 flex-col">
        <header className="sticky top-0 z-40 flex items-center justify-between gap-3 border-b bg-card px-4 py-2.5 md:px-6">
          <div className="flex items-center gap-2 md:hidden">
            <span
              aria-hidden="true"
              className="grid h-8 w-8 place-items-center rounded-md bg-ink font-display text-xs font-bold text-paper"
            >
              AC
            </span>
            <span className="font-display text-sm font-semibold">Acharya CLUB</span>
          </div>
          <div className="hidden text-sm text-muted-foreground md:block" />
          <div className="flex items-center gap-1.5">
            <NotificationBell role={role} />
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="sm" className="gap-2" aria-label="Account menu">
                  <UserRound aria-hidden="true" className="h-4 w-4" />
                  <span className="hidden max-w-32 truncate sm:inline">{user?.name}</span>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <DropdownMenuLabel>
                  <p className="truncate">{user?.name}</p>
                  <p className="truncate text-xs font-normal text-muted-foreground">
                    {user?.email} · {user?.role}
                  </p>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem onSelect={() => navigate(`/${role}/notifications`)}>
                  <Bell aria-hidden="true" className="mr-2 h-4 w-4" />
                  Notifications
                </DropdownMenuItem>
                <DropdownMenuItem onSelect={() => setPasswordOpen(true)}>
                  <KeyRound aria-hidden="true" className="mr-2 h-4 w-4" />
                  Change password
                </DropdownMenuItem>
                <DropdownMenuItem onSelect={handleLogout}>
                  <LogOut aria-hidden="true" className="mr-2 h-4 w-4" />
                  Log out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </header>

        <main id="main-content" className="flex-1 px-4 py-6 pb-24 md:px-6 md:pb-6">
          <Outlet />
        </main>

        <nav
          aria-label="Primary"
          className="fixed inset-x-0 bottom-0 z-40 flex border-t bg-card md:hidden"
        >
          {items.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                cn(
                  'flex flex-1 flex-col items-center gap-0.5 py-2 text-[11px] text-muted-foreground',
                  isActive && 'font-semibold text-ink',
                )
              }
            >
              <item.icon aria-hidden="true" className="h-5 w-5" />
              {item.label}
            </NavLink>
          ))}
        </nav>
      </div>
    </div>
  );
}
