import { useState } from 'react';
import { toast } from 'sonner';
import { isApiError } from '@/api/errors';
import { SearchInput } from '@/components/common/SearchInput';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Skeleton } from '@/components/ui/skeleton';
import { useAssignCoordinator } from '@/hooks/useEvents';
import { useTeachers } from '@/hooks/useUsers';
import { cn } from '@/lib/utils';
import type { Event } from '@/types/domain';

export function AssignCoordinatorDialog({
  event,
  open,
  onOpenChange,
}: {
  event: Event;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [search, setSearch] = useState('');
  const [selected, setSelected] = useState<string | null>(null);
  const [serverError, setServerError] = useState<string | null>(null);
  const { data, isPending } = useTeachers({ search, limit: 50 });
  const assign = useAssignCoordinator(event.id);

  const confirm = async () => {
    if (!selected) return;
    setServerError(null);
    try {
      await assign.mutateAsync(selected);
      toast.success('Coordinator assigned.');
      onOpenChange(false);
      setSelected(null);
      setSearch('');
    } catch (error) {
      setServerError(isApiError(error) ? error.message : 'Could not assign the coordinator.');
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Assign a coordinator</DialogTitle>
          <DialogDescription>
            The coordinator reviews registrations and marks attendance for “{event.title}”. Only
            active teachers can coordinate.
          </DialogDescription>
        </DialogHeader>
        <SearchInput
          value={search}
          onDebouncedChange={setSearch}
          placeholder="Search teachers…"
          label="Search teachers"
        />
        <div
          role="radiogroup"
          aria-label="Teachers"
          className="max-h-64 space-y-1 overflow-y-auto rounded-md border p-1"
        >
          {isPending ? (
            <div className="space-y-2 p-2">
              <Skeleton className="h-9" />
              <Skeleton className="h-9" />
            </div>
          ) : !data || data.items.length === 0 ? (
            <p className="p-3 text-sm text-muted-foreground">No active teachers match.</p>
          ) : (
            data.items.map((teacher) => (
              <label
                key={teacher.id}
                className={cn(
                  'flex cursor-pointer flex-col rounded-sm px-2.5 py-1.5 text-sm transition-colors has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-ring',
                  selected === teacher.id ? 'bg-ink text-paper' : 'hover:bg-secondary',
                )}
              >
                <input
                  type="radio"
                  name="coordinator"
                  value={teacher.id}
                  checked={selected === teacher.id}
                  onChange={() => setSelected(teacher.id)}
                  className="sr-only"
                />
                <span className="font-medium">{teacher.name}</span>
                <span
                  className={cn(
                    'text-xs',
                    selected === teacher.id ? 'text-paper/70' : 'text-muted-foreground',
                  )}
                >
                  {teacher.email}
                </span>
              </label>
            ))
          )}
        </div>
        {serverError && (
          <p role="alert" className="text-sm text-status-rejected">
            {serverError}
          </p>
        )}
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={assign.isPending}>
            Cancel
          </Button>
          <Button onClick={confirm} disabled={!selected || assign.isPending}>
            {assign.isPending ? 'Assigning…' : 'Assign coordinator'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
