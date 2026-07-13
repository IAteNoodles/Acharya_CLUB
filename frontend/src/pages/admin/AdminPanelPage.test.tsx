import { http, HttpResponse } from 'msw';
import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { BASE, PENDING_TEACHER } from '@/test/msw/fixtures';
import { server } from '@/test/msw/server';
import { renderWithProviders } from '@/test/renderWithProviders';
import { AdminPanelPage } from './AdminPanelPage';

describe('AdminPanelPage', () => {
  it('lists pending teachers from the legacy users envelope and the directory', async () => {
    renderWithProviders(<AdminPanelPage />, { route: '/admin/panel', path: '/admin/panel' });

    expect(await screen.findByText('Prof. New')).toBeInTheDocument();
    expect(await screen.findByText('Prof. Rao')).toBeInTheDocument();
  });

  it('approves a pending teacher after confirmation', async () => {
    const user = userEvent.setup();
    const approved = vi.fn();
    server.use(
      http.patch(`${BASE}/users/:id/approve`, ({ params }) => {
        approved(params.id);
        return HttpResponse.json({
          success: true,
          data: { ...PENDING_TEACHER, status: 'active' },
        });
      }),
    );
    renderWithProviders(<AdminPanelPage />, { route: '/admin/panel', path: '/admin/panel' });

    await user.click(await screen.findByRole('button', { name: /^approve$/i }));
    const dialog = await screen.findByRole('dialog');
    expect(
      within(dialog).getByText(/they will be notified and can sign in/i),
    ).toBeInTheDocument();
    await user.click(within(dialog).getByRole('button', { name: /^approve$/i }));

    await waitFor(() => expect(approved).toHaveBeenCalledWith(PENDING_TEACHER.id));
  });
});
