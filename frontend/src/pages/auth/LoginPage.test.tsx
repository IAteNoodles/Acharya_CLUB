import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { useAuthStore } from '@/stores/auth.store';
import { renderWithProviders } from '@/test/renderWithProviders';
import { LoginPage } from './LoginPage';

describe('LoginPage', () => {
  it('shows an inline error for invalid credentials (401)', async () => {
    const user = userEvent.setup();
    renderWithProviders(<LoginPage />, { route: '/login', path: '/login' });

    await user.type(screen.getByLabelText(/college email/i), 'sita@college.edu');
    await user.type(screen.getByLabelText(/password/i), 'WrongPass1');
    await user.click(screen.getByRole('button', { name: /sign in/i }));

    expect(await screen.findByText('Invalid email or password')).toBeInTheDocument();
    expect(useAuthStore.getState().status).not.toBe('authed');
    expect(useAuthStore.getState().user).toBeNull();
  });

  it('shows the pending-approval banner on 403', async () => {
    const user = userEvent.setup();
    renderWithProviders(<LoginPage />, { route: '/login', path: '/login' });

    await user.type(screen.getByLabelText(/college email/i), 'pending@college.edu');
    await user.type(screen.getByLabelText(/password/i), 'Whatever1');
    await user.click(screen.getByRole('button', { name: /sign in/i }));

    expect(
      await screen.findByText(/your account is pending admin approval/i),
    ).toBeInTheDocument();
    expect(screen.getByText('Account is not active')).toBeInTheDocument();
  });

  it('signs in and stores the session on success', async () => {
    const user = userEvent.setup();
    renderWithProviders(<LoginPage />, { route: '/login', path: '/login' });

    await user.type(screen.getByLabelText(/college email/i), 'sita@college.edu');
    await user.type(screen.getByLabelText(/password/i), 'Correct@123');
    await user.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => expect(useAuthStore.getState().status).toBe('authed'));
    expect(useAuthStore.getState().user?.role).toBe('student');
    expect(localStorage.getItem('acharya.refreshToken')).toBe('refresh-1');
  });

  it('validates the form before submitting', async () => {
    const user = userEvent.setup();
    renderWithProviders(<LoginPage />, { route: '/login', path: '/login' });

    await user.click(screen.getByRole('button', { name: /sign in/i }));
    expect(await screen.findByText(/enter a valid email address/i)).toBeInTheDocument();
    expect(screen.getByText(/enter your password/i)).toBeInTheDocument();
  });
});
