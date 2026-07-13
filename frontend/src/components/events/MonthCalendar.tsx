import {
  addMonths,
  eachDayOfInterval,
  endOfMonth,
  endOfWeek,
  format,
  isSameDay,
  isSameMonth,
  isWithinInterval,
  parseISO,
  startOfDay,
  startOfMonth,
  startOfWeek,
} from 'date-fns';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import type { EventListItem } from '@/types/domain';

const TONE: Record<string, string> = {
  pending: 'bg-status-vivid-pending',
  in_college: 'bg-status-vivid-approved-in',
  out_college: 'bg-status-vivid-approved-out',
  draft: 'bg-status-vivid-draft',
};

function eventTone(event: EventListItem): string | null {
  if (event.status === 'rejected') return null;
  if (event.status === 'pending') return TONE.pending;
  if (event.status === 'draft') return TONE.draft;
  return TONE[event.event_type];
}

export function MonthCalendar({ events }: { events: EventListItem[] }) {
  const [month, setMonth] = useState(() => startOfMonth(new Date()));

  const days = eachDayOfInterval({
    start: startOfWeek(month, { weekStartsOn: 1 }),
    end: endOfWeek(endOfMonth(month), { weekStartsOn: 1 }),
  });

  const eventsOn = (day: Date) =>
    events.filter((event) => {
      if (!eventTone(event)) return false;
      const start = startOfDay(parseISO(event.start_date));
      const end = startOfDay(parseISO(event.end_date));
      return isWithinInterval(startOfDay(day), { start, end: end < start ? start : end });
    });

  return (
    <div className="rounded-md border bg-card p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="font-display text-base font-semibold">{format(month, 'MMMM yyyy')}</h3>
        <div className="flex gap-1">
          <Button
            variant="outline"
            size="icon"
            aria-label="Previous month"
            onClick={() => setMonth((current) => addMonths(current, -1))}
          >
            <ChevronLeft aria-hidden="true" className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            size="icon"
            aria-label="Next month"
            onClick={() => setMonth((current) => addMonths(current, 1))}
          >
            <ChevronRight aria-hidden="true" className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-7 gap-px overflow-hidden rounded-sm border bg-border text-xs">
        {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map((weekday) => (
          <div key={weekday} className="bg-secondary px-1.5 py-1 text-center font-semibold uppercase tracking-wide text-muted-foreground">
            <abbr title={weekday} className="no-underline">
              {weekday}
            </abbr>
          </div>
        ))}
        {days.map((day) => {
          const dayEvents = eventsOn(day);
          const isToday = isSameDay(day, new Date());
          return (
            <div
              key={day.toISOString()}
              className={cn(
                'min-h-16 bg-card p-1',
                !isSameMonth(day, month) && 'bg-paper text-muted-foreground',
              )}
            >
              <p
                className={cn(
                  'mb-0.5 grid h-5 w-5 place-items-center rounded-full tabular-nums',
                  isToday && 'bg-ink font-bold text-paper',
                )}
              >
                {format(day, 'd')}
              </p>
              <ul className="space-y-0.5">
                {dayEvents.slice(0, 2).map((event) => (
                  <li key={event.id}>
                    <Link
                      to={`/admin/events/${event.id}`}
                      className="flex items-center gap-1 truncate rounded-sm px-0.5 hover:bg-secondary"
                      title={event.title}
                    >
                      <span
                        aria-hidden="true"
                        className={cn('h-1.5 w-1.5 shrink-0 rounded-full', eventTone(event))}
                      />
                      <span className="truncate">{event.title}</span>
                    </Link>
                  </li>
                ))}
                {dayEvents.length > 2 && (
                  <li className="px-0.5 text-muted-foreground">+{dayEvents.length - 2} more</li>
                )}
              </ul>
            </div>
          );
        })}
      </div>

      <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
        <li className="flex items-center gap-1.5">
          <span aria-hidden="true" className="h-2 w-2 rounded-full bg-status-vivid-approved-in" /> In-College
        </li>
        <li className="flex items-center gap-1.5">
          <span aria-hidden="true" className="h-2 w-2 rounded-full bg-status-vivid-approved-out" /> Out-College
        </li>
        <li className="flex items-center gap-1.5">
          <span aria-hidden="true" className="h-2 w-2 rounded-full bg-status-vivid-pending" /> Pending
        </li>
        <li className="flex items-center gap-1.5">
          <span aria-hidden="true" className="h-2 w-2 rounded-full bg-status-vivid-draft" /> Draft
        </li>
      </ul>
    </div>
  );
}
