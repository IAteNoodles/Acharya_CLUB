import { createBrowserRouter, Navigate } from 'react-router-dom';
import { AuthLayout } from '@/layouts/AuthLayout';
import { PortalLayout } from '@/layouts/PortalLayout';
import { ROLE_HOME } from '@/lib/constants';
import { AdminPanelPage } from '@/pages/admin/AdminPanelPage';
import { DashboardPage as AdminDashboardPage } from '@/pages/admin/DashboardPage';
import { EventDetailPage as AdminEventDetailPage } from '@/pages/admin/EventDetailPage';
import { EventsPage as AdminEventsPage } from '@/pages/admin/EventsPage';
import { LoginPage } from '@/pages/auth/LoginPage';
import { SignupPage } from '@/pages/auth/SignupPage';
import { NotificationsPage } from '@/pages/shared/NotificationsPage';
import { DashboardPage as StudentDashboardPage } from '@/pages/student/DashboardPage';
import { EventDetailPage as StudentEventDetailPage } from '@/pages/student/EventDetailPage';
import { EventsPage as StudentEventsPage } from '@/pages/student/EventsPage';
import { MyAttendancePage } from '@/pages/student/MyAttendancePage';
import { MyRegistrationsPage } from '@/pages/student/MyRegistrationsPage';
import { ForbiddenPage } from '@/pages/system/ForbiddenPage';
import { NotFoundPage } from '@/pages/system/NotFoundPage';
import { DashboardPage as TeacherDashboardPage } from '@/pages/teacher/DashboardPage';
import { EventDetailPage as TeacherEventDetailPage } from '@/pages/teacher/EventDetailPage';
import { EventsPage as TeacherEventsPage } from '@/pages/teacher/EventsPage';
import { useAuthStore } from '@/stores/auth.store';
import { ProtectedRoute } from './ProtectedRoute';
import { RoleRoute } from './RoleRoute';

function RootRedirect() {
  const status = useAuthStore((s) => s.status);
  const user = useAuthStore((s) => s.user);
  if (status === 'booting') return null;
  if (status === 'authed' && user) return <Navigate to={ROLE_HOME[user.role]} replace />;
  return <Navigate to="/login" replace />;
}

export const router = createBrowserRouter([
  { path: '/', element: <RootRedirect /> },
  {
    element: <AuthLayout />,
    children: [
      { path: '/login', element: <LoginPage /> },
      { path: '/signup', element: <SignupPage /> },
    ],
  },
  {
    element: <ProtectedRoute />,
    children: [
      {
        element: <RoleRoute allow={['student']} />,
        children: [
          {
            path: '/student',
            element: <PortalLayout role="student" />,
            children: [
              { index: true, element: <StudentDashboardPage /> },
              { path: 'events', element: <StudentEventsPage /> },
              { path: 'events/:id', element: <StudentEventDetailPage /> },
              { path: 'participation', element: <MyRegistrationsPage roleType="participant" /> },
              { path: 'volunteering', element: <MyRegistrationsPage roleType="volunteer" /> },
              { path: 'attendance', element: <MyAttendancePage /> },
              { path: 'notifications', element: <NotificationsPage /> },
            ],
          },
        ],
      },
      {
        element: <RoleRoute allow={['teacher']} />,
        children: [
          {
            path: '/teacher',
            element: <PortalLayout role="teacher" />,
            children: [
              { index: true, element: <TeacherDashboardPage /> },
              { path: 'events', element: <TeacherEventsPage /> },
              { path: 'events/:id', element: <TeacherEventDetailPage /> },
              { path: 'notifications', element: <NotificationsPage /> },
            ],
          },
        ],
      },
      {
        element: <RoleRoute allow={['admin']} />,
        children: [
          {
            path: '/admin',
            element: <PortalLayout role="admin" />,
            children: [
              { index: true, element: <AdminDashboardPage /> },
              { path: 'events', element: <AdminEventsPage /> },
              { path: 'events/:id', element: <AdminEventDetailPage /> },
              { path: 'panel', element: <AdminPanelPage /> },
              { path: 'notifications', element: <NotificationsPage /> },
            ],
          },
        ],
      },
    ],
  },
  { path: '/forbidden', element: <ForbiddenPage /> },
  { path: '*', element: <NotFoundPage /> },
]);
