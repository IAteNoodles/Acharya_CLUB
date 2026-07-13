import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { useAuthStore } from '@/stores/auth.store';
import { renderWithProviders } from '@/test/renderWithProviders';
import { SignupPage } from './SignupPage';

async function fillForm(user: ReturnType<typeof userEvent.setup>, email: string) {
  await user.type(screen.getByLabelText(/full name/i), 'New Person');
  await user.type(screen.getByLabelText(/college email/i), email);
  await user.type(screen.getByLabelText(/^password$/i), 'Secret@123');
  await user.type(screen.getByLabelText(/confirm password/i), 'Secret@123');
}

describe('SignupPage', () => {
  it('rejects non-college emails client-side', async () => {
    const user = userEvent.setup();
    renderWithProviders(<SignupPage />, { route: '/signup', path: '/signup' });

    await fillForm(user, 'someone@gmail.com');
    await user.click(screen.getByRole('button', { name: /create account/i }));
    expect(await screen.findByText(/use your @college\.edu email/i)).toBeInTheDocument();
  });

  it('rejects mismatched passwords', async () => {
    const user = userEvent.setup();
    renderWithProviders(<SignupPage />, { route: '/signup', path: '/signup' });

    await user.type(screen.getByLabelText(/full name/i), 'New Person');
    await user.type(screen.getByLabelText(/college email/i), 'new@college.edu');
    await user.type(screen.getByLabelText(/^password$/i), 'Secret@123');
    await user.type(screen.getByLabelText(/confirm password/i), 'Different@123');
    await user.click(screen.getByRole('button', { name: /create account/i }));
    expect(await screen.findByText(/passwords do not match/i)).toBeInTheDocument();
  });

  it('signs a student straight into the app', async () => {
    const user = userEvent.setup();
    renderWithProviders(<SignupPage />, { route: '/signup', path: '/signup' });

    await fillForm(user, 'fresh@college.edu');
    await user.click(screen.getByRole('button', { name: /create account/i }));

    await waitFor(() => expect(useAuthStore.getState().status).toBe('authed'));
  });

  it('shows the awaiting-approval screen after teacher signup without entering the app', async () => {
    const user = userEvent.setup();
    renderWithProviders(<SignupPage />, { route: '/signup', path: '/signup' });

    await user.click(screen.getByRole('radio', { name: /teacher/i }));
    expect(
      screen.getByText(/your account will be active after admin approval/i),
    ).toBeInTheDocument();

    await fillForm(user, 'newteacher@college.edu');
    await user.click(screen.getByRole('button', { name: /create account/i }));

    expect(
      await screen.findByRole('heading', { name: /account created — awaiting approval/i }),
    ).toBeInTheDocument();
    expect(useAuthStore.getState().status).toBe('guest');
    expect(localStorage.getItem('acharya.refreshToken')).toBeNull();
  });

  it('maps a 409 duplicate email onto the email field', async () => {
    const user = userEvent.setup();
    renderWithProviders(<SignupPage />, { route: '/signup', path: '/signup' });

    await fillForm(user, 'taken@college.edu');
    await user.click(screen.getByRole('button', { name: /create account/i }));
    expect(await screen.findByText(/email already registered/i)).toBeInTheDocument();
  });
});
