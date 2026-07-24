import { useState } from 'react';
import { toast } from 'sonner';
import { isApiError } from '@/api/errors';
import { Button } from '@/components/ui/button';
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet';
import { useRegister } from '@/hooks/useRegistrations';
import { cn } from '@/lib/utils';
import type { Event } from '@/types/domain';
import type { RegistrationRole } from '@/types/enums';

const ROLE_COPY: Record<RegistrationRole, { title: string; blurb: string }> = {
  participant: { title: 'Participant', blurb: 'Take part in the event itself.' },
  volunteer: { title: 'Volunteer', blurb: 'Help organize and run the event.' },
};

export function JoinEventSheet({ event }: { event: Event }) {
  const [open, setOpen] = useState(false);
  const [role, setRole] = useState<RegistrationRole | null>(null);
  const [serverError, setServerError] = useState<string | null>(null);
  const registerMutation = useRegister(event.id);

  const availableRoles: RegistrationRole[] =
    event.category === 'both' ? ['participant', 'volunteer'] : [event.category];

  const confirm = async () => {
    if (!role) return;
    setServerError(null);
    try {
      await registerMutation.mutateAsync(role);
      toast.success('Request sent — the coordinator will review it.');
      setOpen(false);
      setRole(null);
    } catch (error) {
      setServerError(
        isApiError(error) ? error.message : 'Could not send your request. Try again.',
      );
    }
  };

  return (
    <Sheet
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        if (!next) {
          setRole(null);
          setServerError(null);
        }
      }}
    >
      <SheetTrigger asChild>
        <Button>Join event</Button>
      </SheetTrigger>
      <SheetContent side="bottom" className="mx-auto max-w-lg rounded-t-lg">
        <SheetHeader className="text-left">
          <SheetTitle>Join “{event.title}”</SheetTitle>
          <SheetDescription>
            Pick how you want to take part. Your request stays pending until the coordinator
            accepts it.
          </SheetDescription>
        </SheetHeader>
        <div className="mt-4 grid gap-2" role="radiogroup" aria-label="Join as">
          {availableRoles.map((option) => (
            <label
              key={option}
              className={cn(
                'flex cursor-pointer flex-col rounded-md border p-3 transition-colors has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-ring',
                role === option ? 'border-ink bg-secondary' : 'hover:bg-secondary/50',
              )}
            >
              <input
                type="radio"
                name="join-role"
                value={option}
                checked={role === option}
                onChange={() => setRole(option)}
                className="sr-only"
              />
              <span className="text-sm font-semibold">{ROLE_COPY[option].title}</span>
              <span className="text-sm text-muted-foreground">{ROLE_COPY[option].blurb}</span>
            </label>
          ))}
        </div>
        {serverError && (
          <p role="alert" className="mt-3 text-sm text-status-rejected">
            {serverError}
          </p>
        )}
        <Button
          className="mt-4 w-full"
          disabled={!role || registerMutation.isPending}
          onClick={confirm}
        >
          {registerMutation.isPending ? 'Sending request…' : 'Send request'}
        </Button>
      </SheetContent>
    </Sheet>
  );
}
