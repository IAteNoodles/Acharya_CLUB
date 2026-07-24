import { zodResolver } from '@hookform/resolvers/zod';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { toast } from 'sonner';
import { z } from 'zod';
import { changePassword } from '@/api/auth.api';
import { isApiError } from '@/api/errors';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

const schema = z
  .object({
    currentPassword: z.string().min(1, 'Enter your current password'),
    newPassword: z
      .string()
      .min(8, 'Password must be at least 8 characters')
      .max(100, 'Password must not exceed 100 characters'),
    confirmPassword: z.string(),
  })
  .refine((values) => values.newPassword === values.confirmPassword, {
    message: 'Passwords do not match',
    path: ['confirmPassword'],
  })
  .refine((values) => values.newPassword !== values.currentPassword, {
    message: 'New password must differ from the current one',
    path: ['newPassword'],
  });

type FormValues = z.infer<typeof schema>;

export function ChangePasswordDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    setError,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const close = (next: boolean) => {
    onOpenChange(next);
    if (!next) {
      reset();
      setFormError(null);
    }
  };

  const onSubmit = async (values: FormValues) => {
    setFormError(null);
    try {
      await changePassword(values.currentPassword, values.newPassword);
      toast.success('Password changed.');
      close(false);
    } catch (error) {
      if (isApiError(error) && error.status === 401) {
        setError('currentPassword', { message: 'Current password is incorrect' });
      } else if (isApiError(error) && error.fieldErrors) {
        for (const [field, message] of Object.entries(error.fieldErrors)) {
          if (field === 'currentPassword' || field === 'newPassword') {
            setError(field, { message });
          }
        }
        setFormError(error.message);
      } else if (isApiError(error)) {
        setFormError(error.message);
      } else {
        setFormError('Could not change your password. Try again.');
      }
    }
  };

  return (
    <Dialog open={open} onOpenChange={close}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Change password</DialogTitle>
          <DialogDescription>
            Enter your current password and choose a new one. You'll stay signed in.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="current-password">Current password</Label>
            <Input
              id="current-password"
              type="password"
              autoComplete="current-password"
              aria-invalid={!!errors.currentPassword}
              aria-describedby={errors.currentPassword ? 'current-password-error' : undefined}
              {...register('currentPassword')}
            />
            {errors.currentPassword && (
              <p id="current-password-error" className="text-sm text-status-rejected">
                {errors.currentPassword.message}
              </p>
            )}
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="new-password">New password</Label>
            <Input
              id="new-password"
              type="password"
              autoComplete="new-password"
              aria-invalid={!!errors.newPassword}
              aria-describedby={errors.newPassword ? 'new-password-error' : undefined}
              {...register('newPassword')}
            />
            {errors.newPassword && (
              <p id="new-password-error" className="text-sm text-status-rejected">
                {errors.newPassword.message}
              </p>
            )}
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="confirm-new-password">Confirm new password</Label>
            <Input
              id="confirm-new-password"
              type="password"
              autoComplete="new-password"
              aria-invalid={!!errors.confirmPassword}
              aria-describedby={errors.confirmPassword ? 'confirm-new-password-error' : undefined}
              {...register('confirmPassword')}
            />
            {errors.confirmPassword && (
              <p id="confirm-new-password-error" className="text-sm text-status-rejected">
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
            {isSubmitting ? 'Saving…' : 'Change password'}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}
