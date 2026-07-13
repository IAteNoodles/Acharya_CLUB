import { http, HttpResponse } from 'msw';
import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { BASE, EVENT_ID, paginated, REGISTRATION_WITH_STUDENT } from '@/test/msw/fixtures';
import { server } from '@/test/msw/server';
import { renderWithProviders } from '@/test/renderWithProviders';
import { EventRegistrationsTable } from './EventRegistrationsTable';

describe('EventRegistrationsTable', () => {
  it('lists registrations with student details and pending actions', async () => {
    renderWithProviders(<EventRegistrationsTable eventId={EVENT_ID} />);

    expect(await screen.findByText('Sita Sharma')).toBeInTheDocument();
    expect(screen.getByText('sita@college.edu')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^accept$/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^reject$/i })).toBeInTheDocument();
  });

  it('accepts a registration after confirmation', async () => {
    const user = userEvent.setup();
    const accepted = vi.fn();
    server.use(
      http.patch(`${BASE}/registrations/:id/accept`, () => {
        accepted();
        return HttpResponse.json({
          success: true,
          data: { ...REGISTRATION_WITH_STUDENT, status: 'accepted' },
        });
      }),
    );
    renderWithProviders(<EventRegistrationsTable eventId={EVENT_ID} />);

    await user.click(await screen.findByRole('button', { name: /^accept$/i }));
    const dialog = await screen.findByRole('dialog');
    expect(within(dialog).getByText(/the student will be notified/i)).toBeInTheDocument();
    await user.click(within(dialog).getByRole('button', { name: /^accept$/i }));

    await waitFor(() => expect(accepted).toHaveBeenCalledTimes(1));
  });

  it('runs bulk accept sequentially over the selected pending rows', async () => {
    const user = userEvent.setup();
    const second = {
      ...REGISTRATION_WITH_STUDENT,
      id: '77777777-7777-4777-8777-777777777777',
      student: {
        id: '88888888-8888-4888-8888-888888888888',
        name: 'Arun Iyer',
        email: 'arun@college.edu',
      },
    };
    const acceptedIds: string[] = [];
    server.use(
      http.get(`${BASE}/registrations/event/:eventId`, () =>
        HttpResponse.json(paginated([REGISTRATION_WITH_STUDENT, second])),
      ),
      http.patch(`${BASE}/registrations/:id/accept`, ({ params }) => {
        acceptedIds.push(params.id as string);
        return HttpResponse.json({
          success: true,
          data: { ...REGISTRATION_WITH_STUDENT, status: 'accepted' },
        });
      }),
    );
    renderWithProviders(<EventRegistrationsTable eventId={EVENT_ID} />);

    await user.click(await screen.findByRole('checkbox', { name: /select all pending/i }));
    await user.click(screen.getByRole('button', { name: /accept \(2\)/i }));

    await waitFor(() => expect(acceptedIds).toHaveLength(2));
    expect(new Set(acceptedIds).size).toBe(2);
  });
});
