import { useState } from 'react';
import { toast } from 'sonner';
import { EventForm, type EventFormValues } from '@/components/events/EventForm';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { useUpdateEvent } from '@/hooks/useEvents';
import { toDateInputValue } from '@/lib/format';
import type { Event } from '@/types/domain';

export function EditEventDialog({ event }: { event: Event }) {
  const [open, setOpen] = useState(false);
  const updateEvent = useUpdateEvent(event.id);

  const submit = async (values: EventFormValues) => {
    await updateEvent.mutateAsync({
      title: values.title,
      description: values.description || null,
      category: values.category,
      venue: values.venue,
      start_date: values.start_date,
      end_date: values.end_date,
    });
    toast.success('Event updated.');
    setOpen(false);
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline">Edit details</Button>
      </DialogTrigger>
      <DialogContent className="max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Edit “{event.title}”</DialogTitle>
          <DialogDescription>
            Type and status can't be changed here — use the approve/reject actions for status.
          </DialogDescription>
        </DialogHeader>
        <EventForm
          submitLabel="Save changes"
          requireFutureStart={false}
          defaultValues={{
            title: event.title,
            description: event.description ?? '',
            venue: event.venue ?? '',
            category: event.category,
            start_date: toDateInputValue(event.start_date),
            end_date: toDateInputValue(event.end_date),
          }}
          onSubmit={submit}
        />
      </DialogContent>
    </Dialog>
  );
}
