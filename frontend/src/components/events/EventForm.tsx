import { zodResolver } from '@hookform/resolvers/zod';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { isApiError } from '@/api/errors';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';

const baseSchema = z.object({
  title: z.string().trim().min(1, 'Give the event a title').max(200, 'Keep the title under 200 characters'),
  description: z.string().trim().max(5000, 'Keep the description under 5000 characters').optional(),
  venue: z
    .string()
    .trim()
    .min(1, 'Where does the event take place?')
    .max(300, 'Keep the venue under 300 characters'),
  category: z.enum(['volunteer', 'participant', 'both'], { message: 'Pick who can join' }),
  start_date: z.string().min(1, 'Pick a start date'),
  end_date: z.string().min(1, 'Pick an end date'),
});

export type EventFormValues = z.infer<typeof baseSchema>;

function buildSchema(requireFutureStart: boolean) {
  return baseSchema
    .refine((v) => v.end_date >= v.start_date, {
      message: 'End date must be on or after the start date',
      path: ['end_date'],
    })
    .refine(
      (v) => {
        if (!requireFutureStart) return true;
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        return new Date(`${v.start_date}T00:00:00`) >= today;
      },
      { message: 'Start date must be today or later', path: ['start_date'] },
    );
}

const CATEGORY_LABELS: Record<EventFormValues['category'], string> = {
  both: 'Volunteers and participants',
  volunteer: 'Volunteers only',
  participant: 'Participants only',
};

export function EventForm({
  defaultValues,
  submitLabel,
  requireFutureStart = true,
  onSubmit,
}: {
  defaultValues?: Partial<EventFormValues>;
  submitLabel: string;
  requireFutureStart?: boolean;
  onSubmit: (values: EventFormValues) => Promise<void>;
}) {
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    setError,
    setValue,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<EventFormValues>({
    resolver: zodResolver(buildSchema(requireFutureStart)),
    defaultValues: { category: 'both', ...defaultValues },
  });

  const category = watch('category');

  const submit = async (values: EventFormValues) => {
    setFormError(null);
    try {
      await onSubmit(values);
    } catch (error) {
      if (isApiError(error) && error.fieldErrors) {
        for (const [field, message] of Object.entries(error.fieldErrors)) {
          if (field in baseSchema.shape) {
            setError(field as keyof EventFormValues, { message });
          }
        }
        setFormError(error.message);
      } else if (isApiError(error)) {
        setFormError(error.message);
      } else {
        setFormError('Could not save the event. Try again.');
      }
    }
  };

  return (
    <form onSubmit={handleSubmit(submit)} noValidate className="space-y-4">
      <div className="space-y-1.5">
        <Label htmlFor="event-title">Title</Label>
        <Input
          id="event-title"
          aria-invalid={!!errors.title}
          aria-describedby={errors.title ? 'event-title-error' : undefined}
          {...register('title')}
        />
        {errors.title && (
          <p id="event-title-error" className="text-sm text-status-rejected">
            {errors.title.message}
          </p>
        )}
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="event-description">Description (optional)</Label>
        <Textarea
          id="event-description"
          rows={3}
          aria-invalid={!!errors.description}
          aria-describedby={errors.description ? 'event-description-error' : undefined}
          {...register('description')}
        />
        {errors.description && (
          <p id="event-description-error" className="text-sm text-status-rejected">
            {errors.description.message}
          </p>
        )}
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="event-venue">Venue / organizer</Label>
        <Input
          id="event-venue"
          aria-invalid={!!errors.venue}
          aria-describedby={errors.venue ? 'event-venue-error' : undefined}
          {...register('venue')}
        />
        {errors.venue && (
          <p id="event-venue-error" className="text-sm text-status-rejected">
            {errors.venue.message}
          </p>
        )}
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="event-category">Who can join</Label>
        <Select
          value={category}
          onValueChange={(value) => setValue('category', value as EventFormValues['category'])}
        >
          <SelectTrigger id="event-category" aria-invalid={!!errors.category}>
            <SelectValue placeholder="Pick who can join" />
          </SelectTrigger>
          <SelectContent>
            {(Object.keys(CATEGORY_LABELS) as EventFormValues['category'][]).map((value) => (
              <SelectItem key={value} value={value}>
                {CATEGORY_LABELS[value]}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {errors.category && (
          <p className="text-sm text-status-rejected">{errors.category.message}</p>
        )}
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <Label htmlFor="event-start">Starts</Label>
          <Input
            id="event-start"
            type="date"
            aria-invalid={!!errors.start_date}
            aria-describedby={errors.start_date ? 'event-start-error' : undefined}
            {...register('start_date')}
          />
          {errors.start_date && (
            <p id="event-start-error" className="text-sm text-status-rejected">
              {errors.start_date.message}
            </p>
          )}
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="event-end">Ends</Label>
          <Input
            id="event-end"
            type="date"
            aria-invalid={!!errors.end_date}
            aria-describedby={errors.end_date ? 'event-end-error' : undefined}
            {...register('end_date')}
          />
          {errors.end_date && (
            <p id="event-end-error" className="text-sm text-status-rejected">
              {errors.end_date.message}
            </p>
          )}
        </div>
      </div>

      {formError && (
        <p role="alert" className="text-sm text-status-rejected">
          {formError}
        </p>
      )}

      <Button type="submit" className="w-full" disabled={isSubmitting}>
        {isSubmitting ? 'Saving…' : submitLabel}
      </Button>
    </form>
  );
}
