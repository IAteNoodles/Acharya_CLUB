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
    breakdown: container.querySelector('p.mt-1\\.5'),
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
  events: { total: 4, by_status: { approved: 3, pending: 1 }, by_type: {} },
  registrations: { total: 2, by_status: { pending: 2 } },
  attendance: { total: 0, by_status: {} },
  notifications: { total: 4, unread: 2 },
};

function serveStats(stats: Record<string, unknown>) {
  server.use(
    http.get(`${BASE}/reports/dashboard`, () =>
      HttpResponse.json({ success: true, data: { ...SEEDED, ...stats } }),
    ),
  );
}

describe('DashboardPage', () => {
  it('counts teachers awaiting approval without counting pending students', async () => {
    serveStats({});
    renderWithProviders(<DashboardPage />, { route: '/admin', path: '/admin' });

    await waitFor(() => expect(card(/teachers to approve/i).value).toHaveTextContent('1'));
    expect(card(/events to review/i).value).toHaveTextContent('1');
    expect(card(/registrations to review/i).value).toHaveTextContent('2');
  });

  it('breaks every account total down by status so the headline number is explained', async () => {
    serveStats({});
    renderWithProviders(<DashboardPage />, { route: '/admin', path: '/admin' });

    await waitFor(() => expect(card(/^teacher accounts$/i).value).toHaveTextContent('3'));
    expect(card(/^teacher accounts$/i).breakdown).toHaveTextContent(
      '1 active · 1 pending · 1 rejected',
    );
    expect(card(/^student accounts$/i).value).toHaveTextContent('4');
    expect(card(/^student accounts$/i).breakdown).toHaveTextContent('3 active · 1 pending');
  });

  it('orders the breakdown by lifecycle, not by the order the API returned', async () => {
    serveStats({
      users: {
        ...SEEDED.users,
        by_role_status: { teacher: { rejected: 1, pending: 2, active: 4 } },
      },
    });
    renderWithProviders(<DashboardPage />, { route: '/admin', path: '/admin' });

    await waitFor(() =>
      expect(card(/^teacher accounts$/i).breakdown).toHaveTextContent(
        '4 active · 2 pending · 1 rejected',
      ),
    );
  });

  it('replaces the queues with an all-clear when nothing is pending', async () => {
    serveStats({
      users: { ...SEEDED.users, by_role_status: { teacher: { active: 1 } } },
      events: { total: 4, by_status: { approved: 4 }, by_type: {} },
      registrations: { total: 2, by_status: { accepted: 2 } },
    });
    renderWithProviders(<DashboardPage />, { route: '/admin', path: '/admin' });

    expect(await screen.findByText(/nothing needs a decision/i)).toBeInTheDocument();
    expect(screen.queryByText(/teachers to approve/i)).not.toBeInTheDocument();
  });

  it('shows an em dash rather than a zero before the stats arrive', async () => {
    server.use(
      http.get(`${BASE}/reports/dashboard`, async () => {
        await new Promise((resolve) => setTimeout(resolve, 50));
        return HttpResponse.json({ success: true, data: SEEDED });
      }),
    );
    renderWithProviders(<DashboardPage />, { route: '/admin', path: '/admin' });

    expect(card(/teachers to approve/i).value).toHaveTextContent('—');
    await waitFor(() => expect(card(/teachers to approve/i).value).toHaveTextContent('1'));
  });
});
