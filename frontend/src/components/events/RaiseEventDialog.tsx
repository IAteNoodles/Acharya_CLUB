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
import { rememberMyEventRequest } from '@/lib/myRequests';
import { useAuthStore } from '@/stores/auth.store';

export function RaiseEventDialog({ onCreated }: { onCreated?: () => void }) {
  const [open, setOpen] = useState(false);
  const user = useAuthStore((s) => s.user);
  const createEvent = useCreateEvent();

  const submit = async (values: EventFormValues) => {
    const event = await createEvent.mutateAsync({
      title: values.title,
      description: values.description || null,
      event_type: 'out_college',
      category: 'participant',
      venue: values.venue,
      start_date: values.start_date,
      end_date: values.end_date,
    });
    if (user) rememberMyEventRequest(user.id, event.id);
    toast.success('Submitted for approval — track it under My Requests.');
    setOpen(false);
    onCreated?.();
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
          <Plus aria-hidden="true" className="h-4 w-4" />
          Raise Out-College Event
        </Button>
      </DialogTrigger>
      <DialogContent className="max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Raise an Out-College event</DialogTitle>
          <DialogDescription>
            Submit an event happening outside college. An admin reviews it before it opens for
            registrations. Include a brochure link in the description if you have one.
          </DialogDescription>
        </DialogHeader>
        <EventForm submitLabel="Submit for approval" lockCategory="participant" onSubmit={submit} />
      </DialogContent>
    </Dialog>
  );
}
