import { cn } from '@/lib/utils';
import type { EventType } from '@/types/enums';

type StatusKind = 'event' | 'registration' | 'attendance' | 'user' | 'event-type';

type Tone = 'blue' | 'teal' | 'amber' | 'red' | 'green' | 'grey';

const TONE_CLASSES: Record<Tone, string> = {
  blue: 'text-status-approved-in border-status-approved-in/60 bg-status-approved-in/[0.08]',
  teal: 'text-status-approved-out border-status-approved-out/60 bg-status-approved-out/[0.08]',
  amber: 'text-status-pending border-status-pending/60 bg-status-pending/[0.08]',
  red: 'text-status-rejected border-status-rejected/60 bg-status-rejected/[0.08]',
  green: 'text-status-accepted border-status-accepted/60 bg-status-accepted/[0.08]',
  grey: 'text-status-draft border-status-draft/60 bg-status-draft/[0.08]',
};

function resolveTone(kind: StatusKind, status: string, eventType?: EventType): Tone {
  if (kind === 'event-type') return status === 'in_college' ? 'blue' : 'teal';
  switch (status) {
    case 'approved':
      return eventType === 'out_college' ? 'teal' : 'blue';
    case 'accepted':
    case 'active':
    case 'present':
      return 'green';
    case 'pending':
    case 'late':
      return 'amber';
    case 'rejected':
      return 'red';
    default:
      return 'grey';
  }
}

const LABELS: Record<string, string> = {
  in_college: 'In-College',
  out_college: 'Out-College',
};

export function statusLabel(status: string) {
  return LABELS[status] ?? status.charAt(0).toUpperCase() + status.slice(1);
}

export function StatusBadge({
  kind,
  status,
  eventType,
  className,
}: {
  kind: StatusKind;
  status: string;
  eventType?: EventType;
  className?: string;
}) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-sm border-[1.5px] px-1.5 py-px text-[11px] font-semibold uppercase tracking-[0.08em]',
        TONE_CLASSES[resolveTone(kind, status, eventType)],
        className,
      )}
    >
      {statusLabel(status)}
    </span>
  );
}
