import { http, HttpResponse } from 'msw';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { appError, BASE, EVENT_DETAIL, EVENT_ID, paginated } from '@/test/msw/fixtures';
import { server } from '@/test/msw/server';
import { renderWithProviders } from '@/test/renderWithProviders';
import { EventDetailPage } from './EventDetailPage';

const route = `/student/events/${EVENT_ID}`;
const path = '/student/events/:id';

describe('student EventDetailPage', () => {
  it('renders the event header from the bare-object envelope', async () => {
    server.use(http.get(`${BASE}/registrations/my`, () => HttpResponse.json(paginated([]))));
    renderWithProviders(<EventDetailPage />, { route, path });

    expect(await screen.findByRole('heading', { name: 'Annual Tech Fest' })).toBeInTheDocument();
    expect(screen.getByText('Main Auditorium')).toBeInTheDocument();
    expect(screen.getByText('Unlimited slots')).toBeInTheDocument();
    expect(screen.getByText('Prof. Rao')).toBeInTheDocument();
  });

  it('hides the join button and explains when no coordinator is assigned', async () => {
    server.use(
      http.get(`${BASE}/events/:id`, () =>
        HttpResponse.json({ ...EVENT_DETAIL, coordinator: null }),
      ),
      http.get(`${BASE}/registrations/my`, () => HttpResponse.json(paginated([]))),
    );
    renderWithProviders(<EventDetailPage />, { route, path });

    expect(
      await screen.findByText(/registration opens once a coordinator is assigned/i),
    ).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /join event/i })).not.toBeInTheDocument();
  });

  it('surfaces a 409 from the join request inline in the sheet', async () => {
    const user = userEvent.setup();
    server.use(
      http.get(`${BASE}/registrations/my`, () => HttpResponse.json(paginated([]))),
      http.post(`${BASE}/registrations`, () =>
        HttpResponse.json(appError('CONFLICT', 'Event is at capacity'), { status: 409 }),
      ),
    );
    renderWithProviders(<EventDetailPage />, { route, path });

    await user.click(await screen.findByRole('button', { name: /join event/i }));
    await user.click(await screen.findByRole('radio', { name: /participant/i }));
    await user.click(screen.getByRole('button', { name: /send request/i }));

    expect(await screen.findByText('Event is at capacity')).toBeInTheDocument();
  });

  it('does not offer joining on non-approved events', async () => {
    server.use(
      http.get(`${BASE}/events/:id`, () =>
        HttpResponse.json({ ...EVENT_DETAIL, status: 'pending' }),
      ),
      http.get(`${BASE}/registrations/my`, () => HttpResponse.json(paginated([]))),
    );
    renderWithProviders(<EventDetailPage />, { route, path });

    await screen.findByRole('heading', { name: 'Annual Tech Fest' });
    expect(screen.queryByRole('button', { name: /join event/i })).not.toBeInTheDocument();
  });
});
