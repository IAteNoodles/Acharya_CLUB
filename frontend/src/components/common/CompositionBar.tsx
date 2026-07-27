import { cn } from '@/lib/utils';
import { resolveTone, statusLabel, type StatusKind, type Tone } from './StatusBadge';

const FILL_CLASSES: Record<Tone, string> = {
  blue: 'bg-status-vivid-approved-in',
  teal: 'bg-status-vivid-approved-out',
  amber: 'bg-status-vivid-pending',
  red: 'bg-status-vivid-rejected',
  green: 'bg-status-vivid-accepted',
  grey: 'bg-status-vivid-draft',
};

// Usable first, then waiting, then spent — so the bar reads left to right as a lifecycle.
const STATUS_ORDER = ['active', 'approved', 'accepted', 'present', 'pending', 'draft', 'late', 'rejected', 'absent'];

function byLifecycle([a]: [string, number], [b]: [string, number]) {
  const rank = (s: string) => {
    const i = STATUS_ORDER.indexOf(s);
    return i === -1 ? STATUS_ORDER.length : i;
  };
  return rank(a) - rank(b);
}

export function CompositionBar({
  kind,
  counts,
  className,
}: {
  kind: StatusKind;
  counts: Record<string, number>;
  className?: string;
}) {
  const segments = Object.entries(counts)
    .filter(([, count]) => count > 0)
    .sort(byLifecycle);

  if (segments.length === 0) return null;

  return (
    <div className={cn('mt-2', className)}>
      <div aria-hidden="true" className="flex h-1 gap-px overflow-hidden rounded-full">
        {segments.map(([status, count]) => (
          <span
            key={status}
            style={{ flexGrow: count }}
            className={cn('block', FILL_CLASSES[resolveTone(kind, status)])}
          />
        ))}
      </div>
      <p className="mt-1.5 text-xs text-muted-foreground">
        {segments.map(([status, count]) => `${count} ${statusLabel(status).toLowerCase()}`).join(' · ')}
      </p>
    </div>
  );
}
