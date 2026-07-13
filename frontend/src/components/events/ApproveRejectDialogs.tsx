import { useState } from 'react';
import { toast } from 'sonner';
import { isApiError } from '@/api/errors';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { useApproveEvent, useRejectEvent } from '@/hooks/useEvents';
import type { Event } from '@/types/domain';

export function ApproveEventDialog({
  event,
  open,
  onOpenChange,
}: {
  event: Event;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const approve = useApproveEvent(event.id);
  const [serverError, setServerError] = useState<string | null>(null);

  const confirm = async () => {
    setServerError(null);
    try {
      await approve.mutateAsync(undefined);
      toast.success('Event approved — the creator has been notified.');
      onOpenChange(false);
    } catch (error) {
      setServerError(isApiError(error) ? error.message : 'Could not approve the event.');
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Approve “{event.title}”?</DialogTitle>
          <DialogDescription>
            The event becomes visible to students and the creator is notified.
          </DialogDescription>
        </DialogHeader>
        {!event.coordinator && (
          <p className="rounded-md border border-status-pending/40 bg-status-pending/10 px-3 py-2 text-sm text-status-pending">
            No coordinator assigned yet — students cannot register until a coordinator is
            assigned.
          </p>
        )}
        {serverError && (
          <p role="alert" className="text-sm text-status-rejected">
            {serverError}
          </p>
        )}
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={approve.isPending}>
            Cancel
          </Button>
          <Button onClick={confirm} disabled={approve.isPending}>
            {approve.isPending ? 'Approving…' : 'Approve event'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function RejectEventDialog({
  event,
  open,
  onOpenChange,
}: {
  event: Event;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const reject = useRejectEvent(event.id);
  const [comment, setComment] = useState('');
  const [error, setError] = useState<string | null>(null);

  const confirm = async () => {
    if (!comment.trim()) {
      setError('A reason is required to reject an event.');
      return;
    }
    setError(null);
    try {
      await reject.mutateAsync(comment.trim());
      toast.success('Event rejected — the creator has been notified.');
      onOpenChange(false);
      setComment('');
    } catch (err) {
      setError(isApiError(err) ? err.message : 'Could not reject the event.');
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Reject “{event.title}”?</DialogTitle>
          <DialogDescription>
            The creator is notified that the event was rejected.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-1.5">
          <Label htmlFor="reject-comment">Reason</Label>
          <Textarea
            id="reject-comment"
            rows={3}
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            aria-invalid={!!error}
            aria-describedby="reject-comment-note"
          />
          <p id="reject-comment-note" className="text-xs text-muted-foreground">
            Required. Currently kept for the record only — the requester doesn't see it yet.
          </p>
          {error && (
            <p role="alert" className="text-sm text-status-rejected">
              {error}
            </p>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={reject.isPending}>
            Cancel
          </Button>
          <Button variant="destructive" onClick={confirm} disabled={reject.isPending}>
            {reject.isPending ? 'Rejecting…' : 'Reject event'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
