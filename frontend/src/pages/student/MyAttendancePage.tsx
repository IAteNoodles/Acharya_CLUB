import { ClipboardCheck } from 'lucide-react';
import { useState } from 'react';
import { DataTable, type Column } from '@/components/common/DataTable';
import { EmptyState } from '@/components/common/EmptyState';
import { PageHeader } from '@/components/common/PageHeader';
import { Paginator } from '@/components/common/Paginator';
import { StatusBadge } from '@/components/common/StatusBadge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useMyAttendance } from '@/hooks/useAttendance';
import { useMyRegistrations } from '@/hooks/useRegistrations';
import { formatDate } from '@/lib/format';
import type { AttendanceRecord } from '@/types/domain';
import type { AttendanceStatus } from '@/types/enums';

export function MyAttendancePage() {
  const [eventId, setEventId] = useState<string | undefined>();
  const [status, setStatus] = useState<AttendanceStatus | undefined>();
  const [page, setPage] = useState(1);

  const { data: accepted } = useMyRegistrations({ status: 'accepted', limit: 100 });
  const { data, isPending } = useMyAttendance({ eventId, status, page, limit: 100 });

  const events = (accepted?.items ?? [])
    .map((reg) => reg.event)
    .filter((event): event is NonNullable<typeof event> => !!event);
  const uniqueEvents = [...new Map(events.map((event) => [event.id, event])).values()];

  const rows = data?.items ?? [];
  const presentCount = rows.filter((record) => record.status !== 'absent').length;

  const columns: Column<AttendanceRecord>[] = [
    {
      key: 'event',
      header: 'Event',
      cell: (record) => <span className="font-medium">{record.event?.title ?? '—'}</span>,
    },
    { key: 'date', header: 'Date', cell: (record) => formatDate(record.date) },
    {
      key: 'status',
      header: 'Status',
      cell: (record) => <StatusBadge kind="attendance" status={record.status} />,
    },
  ];

  return (
    <div>
      <PageHeader title="My Attendance" description="Days marked for events you attended." />
      <div className="mb-4 flex flex-col gap-2 sm:flex-row">
        <Select
          value={eventId ?? 'all'}
          onValueChange={(value) => {
            setEventId(value === 'all' ? undefined : value);
            setPage(1);
          }}
        >
          <SelectTrigger className="sm:w-64" aria-label="Filter by event">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All events</SelectItem>
            {uniqueEvents.map((event) => (
              <SelectItem key={event.id} value={event.id}>
                {event.title}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select
          value={status ?? 'all'}
          onValueChange={(value) => {
            setStatus(value === 'all' ? undefined : (value as AttendanceStatus));
            setPage(1);
          }}
        >
          <SelectTrigger className="sm:w-40" aria-label="Filter by status">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            <SelectItem value="present">Present</SelectItem>
            <SelectItem value="absent">Absent</SelectItem>
            <SelectItem value="late">Late</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {rows.length > 0 && (
        <p className="mb-3 text-sm text-muted-foreground tabular-nums">
          Present {presentCount} of {rows.length} marked day{rows.length === 1 ? '' : 's'}
          {data && data.total_pages > 1 ? ' on this page' : ''}.
        </p>
      )}

      <DataTable
        columns={columns}
        rows={rows}
        rowKey={(record) => record.id}
        loading={isPending}
        caption="My attendance records"
        emptyState={
          <EmptyState
            icon={ClipboardCheck}
            title="No attendance yet"
            description="Once a coordinator marks you present or absent at an event, it shows up here."
          />
        }
      />
      {data && <Paginator meta={data} onPageChange={setPage} />}
    </div>
  );
}
