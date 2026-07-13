import { http, HttpResponse } from 'msw';
import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { BASE, legacyList } from '@/test/msw/fixtures';
import { server } from '@/test/msw/server';
import { renderWithProviders } from '@/test/renderWithProviders';
import { EventsPage } from './EventsPage';

describe('student EventsPage', () => {
  it('renders event cards from the legacy flat list envelope', async () => {
    renderWithProviders(<EventsPage />, { route: '/student/events', path: '/student/events' });

    expect(await screen.findByText('Annual Tech Fest')).toBeInTheDocument();
    expect(screen.getByText('12 registered', { exact: false })).toBeInTheDocument();
    expect(screen.getByText('In-College')).toBeInTheDocument();
  });

  it('shows the empty state when no events match', async () => {
    server.use(http.get(`${BASE}/events`, () => HttpResponse.json(legacyList('items', []))));
    renderWithProviders(<EventsPage />, { route: '/student/events', path: '/student/events' });

    expect(await screen.findByText(/no events match/i)).toBeInTheDocument();
  });

  it('offers the raise out-college event action', async () => {
    renderWithProviders(<EventsPage />, { route: '/student/events', path: '/student/events' });
    expect(
      screen.getByRole('button', { name: /raise out-college event/i }),
    ).toBeInTheDocument();
  });
});
