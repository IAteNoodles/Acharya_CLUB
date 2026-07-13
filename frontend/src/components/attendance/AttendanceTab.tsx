import { ClipboardCheck } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { toast } from 'sonner';
import { isApiError } from '@/api/errors';
import { EmptyState } from '@/components/common/EmptyState';
import { StatusBadge } from '@/components/common/StatusBadge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Switch } from '@/components/ui/switch';
import { useEventAttendance, useMarkBulkAttendance } from '@/hooks/useAttendance';
import { useEventRegistrations } from '@/hooks/useRegistrations';
import { formatDate } from '@/lib/format';
import { cn, eventDays } from '@/lib/utils';
import type { Event } from '@/types/domain';

export function AttendanceTab({ event }: { event: Event }) {
  const days = useMemo(() => eventDays(event.start_date, event.end_date), [event]);
  const todayIso = new Date().toISOString().slice(0, 10);
  const defaultDay = days.find((d) => d.date === todayIso) ?? days[0];
  const [selectedDate, setSelectedDate] = useState(defaultDay?.date ?? todayIso);
  const [marks, setMarks] = useState<Record<string, boolean>>({});
  const [dirty, setDirty] = useState(false);

  const { data: roster, isPending: rosterPending, refetch: refetchRoster } = useEventRegistrations(
    event.id,
    { status: 'accepted', limit: 100 },
  );
  const { data: existing, isPending: marksPending } = useEventAttendance(event.id, {
    date: selectedDate,
    limit: 100,
  });
  const save = useMarkBulkAttendance(event.id);

  const students = (roster?.items ?? [])
    .map((reg) => reg.student)
    .filter((student): student is NonNullable<typeof student> => !!student);

  const existingByStudent = useMemo(() => {
    const map = new Map<string, string>();
    for (const record of existing?.items ?? []) map.set(record.student_id, record.status);
    return map;
  }, [existing]);

  useEffect(() => {
    const next: Record<string, boolean> = {};
    for (const student of students) {
      const status = existingByStudent.get(student.id);
      next[student.id] = status === 'present' || status === 'late';
    }
    setMarks(next);
    setDirty(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedDate, existing, roster]);

  const setMark = (studentId: string, present: boolean) => {
    setMarks((prev) => ({ ...prev, [studentId]: present }));
    setDirty(true);
  };

  const markAllPresent = () => {
    setMarks(Object.fromEntries(students.map((student) => [student.id, true])));
    setDirty(true);
  };

  const submit = async () => {
    try {
      const result = await save.mutateAsync({
        date: selectedDate,
        records: students.map((student) => ({
          studentId: student.id,
          present: marks[student.id] ?? false,
        })),
      });
      toast.success(result.message);
      setDirty(false);
    } catch (error) {
      if (isApiError(error) && error.status === 409) {
        toast.error(`${error.message} — refreshing the roster.`);
        refetchRoster();
      } else {
        toast.error(isApiError(error) ? error.message : 'Could not save attendance.');
      }
    }
  };

  if (rosterPending) {
    return (
      <div className="space-y-2">
        <Skeleton className="h-9 w-64" />
        <Skeleton className="h-48 rounded-md" />
      </div>
    );
  }

  if (students.length === 0) {
    return (
      <EmptyState
        icon={ClipboardCheck}
        title="No accepted registrations"
        description="Attendance can be marked once students are accepted for this event."
      />
    );
  }

  const presentCount = students.filter((student) => marks[student.id]).length;

  return (
    <div>
      <div
        role="radiogroup"
        aria-label="Event day"
        className="mb-4 flex flex-wrap gap-1.5"
      >
        {days.map((day) => (
          <label
            key={day.date}
            className={cn(
              'cursor-pointer rounded-md border px-3 py-1.5 text-sm font-medium transition-colors has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-ring',
              selectedDate === day.date
                ? 'border-ink bg-ink text-paper'
                : 'bg-card hover:bg-secondary',
            )}
          >
            <input
              type="radio"
              name="attendance-day"
              value={day.date}
              checked={selectedDate === day.date}
              onChange={() => setSelectedDate(day.date)}
              className="sr-only"
            />
            {day.label}
            <span className={cn('ml-1.5 text-xs', selectedDate === day.date ? 'text-paper/70' : 'text-muted-foreground')}>
              {formatDate(day.date)}
            </span>
          </label>
        ))}
      </div>

      {roster && roster.total > roster.items.length && (
        <p className="mb-3 text-sm text-status-pending">
          Showing the first {roster.items.length} of {roster.total} accepted students.
        </p>
      )}

      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm text-muted-foreground tabular-nums" aria-live="polite">
          {marksPending ? 'Loading marks…' : `${presentCount} of ${students.length} present`}
        </p>
        <Button variant="outline" size="sm" onClick={markAllPresent}>
          Mark all present
        </Button>
      </div>

      <div className="overflow-hidden rounded-md border bg-card">
        <ul className="divide-y">
          {students.map((student) => {
            const wasLate = existingByStudent.get(student.id) === 'late';
            const present = marks[student.id] ?? false;
            return (
              <li key={student.id} className="flex items-center justify-between gap-3 px-4 py-2.5">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium">{student.name}</p>
                  <p className="truncate text-xs text-muted-foreground">{student.email}</p>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  {wasLate && <StatusBadge kind="attendance" status="late" />}
                  <span
                    className={cn(
                      'w-14 text-right text-xs font-semibold uppercase tracking-wide',
                      present ? 'text-status-accepted' : 'text-status-draft',
                    )}
                  >
                    {present ? 'Present' : 'Absent'}
                  </span>
                  <Switch
                    checked={present}
                    onCheckedChange={(checked) => setMark(student.id, checked === true)}
                    aria-label={`Mark ${student.name} ${present ? 'absent' : 'present'} on ${formatDate(selectedDate)}`}
                  />
                </div>
              </li>
            );
          })}
        </ul>
      </div>

      <div className="mt-4 flex items-center justify-end gap-3">
        {dirty && <p className="text-sm text-status-pending">Unsaved changes</p>}
        <Button onClick={submit} disabled={save.isPending || marksPending}>
          {save.isPending ? 'Saving…' : `Save attendance for ${formatDate(selectedDate)}`}
        </Button>
      </div>
    </div>
  );
}
