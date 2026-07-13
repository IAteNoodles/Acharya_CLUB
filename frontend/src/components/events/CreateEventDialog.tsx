import { Plus } from 'lucide-react';
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
import { useCreateEvent } from '@/hooks/useEvents';

export function CreateEventDialog() {
  const [open, setOpen] = useState(false);
  const createEvent = useCreateEvent();

  const submit = async (values: EventFormValues) => {
    await createEvent.mutateAsync({
      title: values.title,
      description: values.description || null,
      event_type: 'in_college',
      category: values.category,
      venue: values.venue,
      start_date: values.start_date,
      end_date: values.end_date,
    });
    toast.success('Event created as a draft — assign a coordinator, then approve it.');
    setOpen(false);
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
          <Plus aria-hidden="true" className="h-4 w-4" />
          Create Event
        </Button>
      </DialogTrigger>
      <DialogContent className="max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Create an In-College event</DialogTitle>
          <DialogDescription>
            The event starts as a draft. Assign a coordinator and approve it to open
            registrations.
          </DialogDescription>
        </DialogHeader>
        <EventForm submitLabel="Create draft" onSubmit={submit} />
      </DialogContent>
    </Dialog>
  );
}
