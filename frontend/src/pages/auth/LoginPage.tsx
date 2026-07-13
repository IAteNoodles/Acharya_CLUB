import { zodResolver } from '@hookform/resolvers/zod';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { z } from 'zod';
import { isApiError } from '@/api/errors';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { ROLE_HOME } from '@/lib/constants';
import { useAuthStore } from '@/stores/auth.store';

const loginSchema = z.object({
  email: z.string().email('Enter a valid email address'),
  password: z.string().min(1, 'Enter your password'),
});

type LoginForm = z.infer<typeof loginSchema>;

export function LoginPage() {
  const login = useAuthStore((s) => s.login);
  const sessionExpired = useAuthStore((s) => s.sessionExpired);
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [formError, setFormError] = useState<string | null>(null);
  const [pendingApproval, setPendingApproval] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginForm>({ resolver: zodResolver(loginSchema) });

  const onSubmit = async (values: LoginForm) => {
    setFormError(null);
    setPendingApproval(null);
    try {
      const user = await login(values.email, values.password);
      const next = searchParams.get('next');
      const home = ROLE_HOME[user.role];
      if (next && next.startsWith(home)) {
        navigate(next, { replace: true });
      } else {
        navigate(home, { replace: true });
      }
    } catch (error) {
      if (isApiError(error) && error.status === 403) {
        setPendingApproval(error.message);
      } else if (isApiError(error) && error.status === 401) {
        setFormError('Invalid email or password');
      } else if (isApiError(error)) {
        setFormError(error.message);
      } else {
        setFormError('Could not sign in. Try again.');
      }
    }
  };

  return (
    <div>
      <h1 className="text-2xl font-semibold">Sign in</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Use your college email to access your portal.
      </p>

      {sessionExpired && (
        <p
          role="status"
          className="mt-4 rounded-md border border-status-pending/40 bg-status-pending/10 px-3 py-2 text-sm text-status-pending"
        >
          Session expired — please log in again.
        </p>
      )}

      {pendingApproval && (
        <div
          role="alert"
          className="mt-4 rounded-md border border-status-pending/40 bg-status-pending/10 px-3 py-2 text-sm"
        >
          <p className="font-medium text-status-pending">
            Your account is pending Admin approval.
          </p>
          <p className="mt-0.5 text-muted-foreground">{pendingApproval}</p>
        </div>
      )}

      <form onSubmit={handleSubmit(onSubmit)} noValidate className="mt-6 space-y-4">
        <div className="space-y-1.5">
          <Label htmlFor="email">College email</Label>
          <Input
            id="email"
            type="email"
            autoComplete="email"
            placeholder="you@college.edu"
            aria-invalid={!!errors.email}
            aria-describedby={errors.email ? 'email-error' : undefined}
            {...register('email')}
          />
          {errors.email && (
            <p id="email-error" className="text-sm text-status-rejected">
              {errors.email.message}
            </p>
          )}
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="password">Password</Label>
          <Input
            id="password"
            type="password"
            autoComplete="current-password"
            aria-invalid={!!errors.password}
            aria-describedby={errors.password ? 'password-error' : undefined}
            {...register('password')}
          />
          {errors.password && (
            <p id="password-error" className="text-sm text-status-rejected">
              {errors.password.message}
            </p>
          )}
        </div>

        {formError && (
          <p role="alert" className="text-sm text-status-rejected">
            {formError}
          </p>
        )}

        <Button type="submit" className="w-full" disabled={isSubmitting}>
          {isSubmitting ? 'Signing in…' : 'Sign in'}
        </Button>
      </form>

      <p className="mt-6 text-sm text-muted-foreground">
        New here?{' '}
        <Link to="/signup" className="font-medium text-ink underline underline-offset-4">
          Create an account
        </Link>
      </p>
    </div>
  );
}
