import { http, HttpResponse } from 'msw';
import { screen, waitFor } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { BASE } from '@/test/msw/fixtures';
import { server } from '@/test/msw/server';
import { renderWithProviders } from '@/test/renderWithProviders';
import { DashboardPage } from './DashboardPage';

function card(label: RegExp) {
  const heading = screen.getByText(label);
  const container = heading.closest('div')?.parentElement as HTMLElement;
  return {
    value: container.querySelector('p.text-2xl'),
    hint: container.querySelector('p.mt-1'),
  };
}

// 1 admin active; teachers 1 active / 1 pending / 1 rejected; students 3 active / 1 pending.
const SEEDED = {
  users: {
    total: 8,
    by_role: { student: 4, teacher: 3, admin: 1 },
    by_status: { active: 5, pending: 2, rejected: 1 },
    by_role_status: {
      student: { active: 3, pending: 1 },
      teacher: { active: 1, pending: 1, rejected: 1 },
      admin: { active: 1 },
    },
  },
  events: { total: 4, by_status: {}, by_type: {} },
  registrations: { total: 2, by_status: { pending: 2 } },
  attendance: { total: 0, by_status: {} },
  notifications: { total: 4, unread: 2 },
};

function serveStats(users: unknown) {
  server.use(
    http.get(`${BASE}/reports/dashboard`, () =>
      HttpResponse.json({ success: true, data: { ...SEEDED, users } }),
    ),
  );
}

describe('DashboardPage', () => {
  it('counts pending teachers without counting pending students', async () => {
    serveStats(SEEDED.users);
    renderWithProviders(<DashboardPage />, { route: '/admin', path: '/admin' });

    await waitFor(() => expect(card(/teacher accounts/i).value).toHaveTextContent('1'));
    expect(card(/^registrations$/i).value).toHaveTextContent('2');
  });

  it('qualifies the student and teacher counts with their own active totals', async () => {
    serveStats(SEEDED.users);
    renderWithProviders(<DashboardPage />, { route: '/admin', path: '/admin' });

    await waitFor(() => expect(card(/^students$/i).value).toHaveTextContent('4'));
    expect(card(/^students$/i).hint).toHaveTextContent('3 active');
    expect(card(/^teachers$/i).value).toHaveTextContent('3');
    expect(card(/^teachers$/i).hint).toHaveTextContent('1 active');
  });

  it('renders a zero rather than an em dash when a role has no pending accounts', async () => {
    serveStats({
      ...SEEDED.users,
      by_role_status: { ...SEEDED.users.by_role_status, teacher: { active: 3 } },
    });
    renderWithProviders(<DashboardPage />, { route: '/admin', path: '/admin' });

    await waitFor(() => expect(card(/^teachers$/i).hint).toHaveTextContent('3 active'));
    expect(card(/teacher accounts/i).value).toHaveTextContent('0');
  });
});
