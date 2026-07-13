import { zodResolver } from '@hookform/resolvers/zod';
import { CircleCheck } from 'lucide-react';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { Link, useNavigate } from 'react-router-dom';
import { z } from 'zod';
import { isApiError } from '@/api/errors';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { COLLEGE_EMAIL_SUFFIX } from '@/lib/constants';
import { cn } from '@/lib/utils';
import { useAuthStore } from '@/stores/auth.store';

const signupSchema = z
  .object({
    name: z.string().trim().min(2, 'Name must be at least 2 characters').max(120, 'Name must not exceed 120 characters'),
    email: z
      .string()
      .email('Enter a valid email address')
      .refine((value) => value.endsWith(COLLEGE_EMAIL_SUFFIX), {
        message: `Use your ${COLLEGE_EMAIL_SUFFIX} email address`,
      }),
    password: z.string().min(8, 'Password must be at least 8 characters').max(100, 'Password must not exceed 100 characters'),
    confirmPassword: z.string(),
    role: z.enum(['student', 'teacher']),
  })
  .refine((values) => values.password === values.confirmPassword, {
    message: 'Passwords do not match',
    path: ['confirmPassword'],
  });

type SignupForm = z.infer<typeof signupSchema>;

export function SignupPage() {
  const signup = useAuthStore((s) => s.signup);
  const navigate = useNavigate();
  const [formError, setFormError] = useState<string | null>(null);
  const [teacherCreated, setTeacherCreated] = useState(false);

  const {
    register,
    handleSubmit,
    setError,
    watch,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<SignupForm>({
    resolver: zodResolver(signupSchema),
    defaultValues: { role: 'student' },
  });

  const role = watch('role');

  const onSubmit = async (values: SignupForm) => {
    setFormError(null);
    try {
      const { enteredApp } = await signup({
        name: values.name,
        email: values.email,
        password: values.password,
        role: values.role,
      });
      if (enteredApp) {
        navigate('/student', { replace: true });
      } else {
        setTeacherCreated(true);
      }
    } catch (error) {
      if (isApiError(error) && error.status === 409) {
        setError('email', { message: error.message });
      } else if (isApiError(error) && error.fieldErrors) {
        for (const [field, message] of Object.entries(error.fieldErrors)) {
          if (field === 'name' || field === 'email' || field === 'password') {
            setError(field, { message });
          }
        }
        setFormError(error.message);
      } else if (isApiError(error)) {
        setFormError(error.message);
      } else {
        setFormError('Could not create your account. Try again.');
      }
    }
  };

  if (teacherCreated) {
    return (
      <div role="status">
        <CircleCheck aria-hidden="true" className="h-8 w-8 text-status-accepted" />
        <h1 className="mt-3 text-2xl font-semibold">Account created — awaiting approval</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Teacher accounts are activated by an administrator. You can sign in once your account is
          approved.
        </p>
        <Button className="mt-6 w-full" onClick={() => navigate('/login')}>
          Back to sign in
        </Button>
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-2xl font-semibold">Create an account</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Students get access immediately. Teacher accounts need admin approval.
      </p>

      <form onSubmit={handleSubmit(onSubmit)} noValidate className="mt-6 space-y-4">
        <fieldset>
          <legend className="mb-1.5 text-sm font-medium">I am a</legend>
          <div className="grid grid-cols-2 gap-2" role="radiogroup">
            {(['student', 'teacher'] as const).map((option) => (
              <label
                key={option}
                className={cn(
                  'flex cursor-pointer items-center justify-center rounded-md border px-3 py-2 text-sm font-medium capitalize transition-colors has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-ring has-[:focus-visible]:ring-offset-1',
                  role === option
                    ? 'border-ink bg-ink text-paper'
                    : 'bg-card text-muted-foreground hover:bg-secondary',
                )}
              >
                <input
                  type="radio"
                  value={option}
                  checked={role === option}
                  onChange={() => setValue('role', option)}
                  className="sr-only"
                  name="role"
                />
                {option}
              </label>
            ))}
          </div>
          {role === 'teacher' && (
            <p className="mt-2 rounded-md border border-status-pending/40 bg-status-pending/10 px-3 py-2 text-sm text-status-pending">
              Your account will be active after Admin approval.
            </p>
          )}
        </fieldset>

        <div className="space-y-1.5">
          <Label htmlFor="name">Full name</Label>
          <Input
            id="name"
            autoComplete="name"
            aria-invalid={!!errors.name}
            aria-describedby={errors.name ? 'name-error' : undefined}
            {...register('name')}
          />
          {errors.name && (
            <p id="name-error" className="text-sm text-status-rejected">
              {errors.name.message}
            </p>
          )}
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="signup-email">College email</Label>
          <Input
            id="signup-email"
            type="email"
            autoComplete="email"
            placeholder={`you${COLLEGE_EMAIL_SUFFIX}`}
            aria-invalid={!!errors.email}
            aria-describedby={errors.email ? 'signup-email-error' : undefined}
            {...register('email')}
          />
          {errors.email && (
            <p id="signup-email-error" className="text-sm text-status-rejected">
              {errors.email.message}
            </p>
          )}
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="signup-password">Password</Label>
          <Input
            id="signup-password"
            type="password"
            autoComplete="new-password"
            aria-invalid={!!errors.password}
            aria-describedby={errors.password ? 'signup-password-error' : undefined}
            {...register('password')}
          />
          {errors.password && (
            <p id="signup-password-error" className="text-sm text-status-rejected">
              {errors.password.message}
            </p>
          )}
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="confirm-password">Confirm password</Label>
          <Input
            id="confirm-password"
            type="password"
            autoComplete="new-password"
            aria-invalid={!!errors.confirmPassword}
            aria-describedby={errors.confirmPassword ? 'confirm-password-error' : undefined}
            {...register('confirmPassword')}
          />
          {errors.confirmPassword && (
            <p id="confirm-password-error" className="text-sm text-status-rejected">
              {errors.confirmPassword.message}
            </p>
          )}
        </div>

        {formError && (
          <p role="alert" className="text-sm text-status-rejected">
            {formError}
          </p>
        )}

        <Button type="submit" className="w-full" disabled={isSubmitting}>
          {isSubmitting ? 'Creating account…' : 'Create account'}
        </Button>
      </form>

      <p className="mt-6 text-sm text-muted-foreground">
        Already registered?{' '}
        <Link to="/login" className="font-medium text-ink underline underline-offset-4">
          Sign in
        </Link>
      </p>
    </div>
  );
}
