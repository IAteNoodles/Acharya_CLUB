import { useQueryClient } from '@tanstack/react-query';
import { UsersRound } from 'lucide-react';
import { useState } from 'react';
import { toast } from 'sonner';
import { isApiError } from '@/api/errors';
import { acceptRegistration, rejectRegistration } from '@/api/registrations.api';
import { ConfirmDialog } from '@/components/common/ConfirmDialog';
import { DataTable, type Column } from '@/components/common/DataTable';
import { EmptyState } from '@/components/common/EmptyState';
import { Paginator } from '@/components/common/Paginator';
import { StatusBadge } from '@/components/common/StatusBadge';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { FilterTabs } from '@/components/common/FilterTabs';
import { useEventRegistrations } from '@/hooks/useRegistrations';
import { formatDate } from '@/lib/format';
import type { Registration } from '@/types/domain';
import type { RegistrationStatus } from '@/types/enums';

const STATUS_TABS = ['all', 'pending', 'accepted', 'rejected'] as const;

type PendingAction = { kind: 'accept' | 'reject'; registration: Registration } | null;

export function EventRegistrationsTable({ eventId }: { eventId: string }) {
  const [status, setStatus] = useState<(typeof STATUS_TABS)[number]>('pending');
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [pendingAction, setPendingAction] = useState<PendingAction>(null);
  const [bulk, setBulk] = useState<{ kind: 'accept' | 'reject'; done: number; total: number } | null>(
    null,
  );
  const [rowBusy, setRowBusy] = useState(false);
  const queryClient = useQueryClient();

  const { data, isPending } = useEventRegistrations(eventId, {
    page,
    limit: 100,
    status: status === 'all' ? undefined : (status as RegistrationStatus),
  });

  const rows = data?.items ?? [];
  const pendingRows = rows.filter((reg) => reg.status === 'pending');
  const allPendingSelected =
    pendingRows.length > 0 && pendingRows.every((reg) => selected.has(reg.id));

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['registrations', 'event', eventId] });
    queryClient.invalidateQueries({ queryKey: ['reports'] });
  };

  const runSingle = async () => {
    if (!pendingAction) return;
    const { kind, registration } = pendingAction;
    setRowBusy(true);
    try {
      await (kind === 'accept' ? acceptRegistration : rejectRegistration)(registration.id);
      toast.success(
        kind === 'accept'
          ? `Accepted ${registration.student?.name ?? 'registration'} — the student has been notified.`
          : `Rejected ${registration.student?.name ?? 'registration'} — the student has been notified.`,
      );
      setPendingAction(null);
    } catch (error) {
      toast.error(isApiError(error) ? error.message : 'Action failed. Try again.');
    } finally {
      setRowBusy(false);
      invalidate();
    }
  };

  const runBulk = async (kind: 'accept' | 'reject') => {
    const ids = pendingRows.filter((reg) => selected.has(reg.id)).map((reg) => reg.id);
    if (ids.length === 0) return;
    setBulk({ kind, done: 0, total: ids.length });
    const failures: string[] = [];
    for (const [index, id] of ids.entries()) {
      try {
        await (kind === 'accept' ? acceptRegistration : rejectRegistration)(id);
      } catch (error) {
        const who = rows.find((reg) => reg.id === id)?.student?.name ?? id;
        failures.push(
          `${who}: ${isApiError(error) ? error.message : 'failed'}`,
        );
      }
      setBulk({ kind, done: index + 1, total: ids.length });
    }
    setBulk(null);
    setSelected(new Set());
    invalidate();
    if (failures.length === 0) {
      toast.success(
        `${kind === 'accept' ? 'Accepted' : 'Rejected'} ${ids.length} registration${ids.length > 1 ? 's' : ''} — students have been notified.`,
      );
    } else {
      toast.error(
        `${failures.length} of ${ids.length} failed: ${failures.slice(0, 3).join('; ')}${failures.length > 3 ? '…' : ''}`,
      );
    }
  };

  const toggle = (id: string, checked: boolean) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (checked) next.add(id);
      else next.delete(id);
      return next;
    });
  };

  const columns: Column<Registration>[] = [
    {
      key: 'select',
      header: (
        <Checkbox
          aria-label="Select all pending registrations"
          checked={allPendingSelected}
          disabled={pendingRows.length === 0}
          onCheckedChange={(checked) =>
            setSelected(checked === true ? new Set(pendingRows.map((reg) => reg.id)) : new Set())
          }
        />
      ),
      className: 'w-10',
      cell: (reg) =>
        reg.status === 'pending' ? (
          <Checkbox
            aria-label={`Select ${reg.student?.name ?? 'registration'}`}
            checked={selected.has(reg.id)}
            onCheckedChange={(checked) => toggle(reg.id, checked === true)}
          />
        ) : null,
    },
    {
      key: 'student',
      header: 'Student',
      cell: (reg) => (
        <div className="min-w-0">
          <p className="truncate font-medium">{reg.student?.name ?? '—'}</p>
          <p className="truncate text-xs text-muted-foreground">{reg.student?.email}</p>
        </div>
      ),
    },
    {
      key: 'role',
      header: 'Role',
      cell: (reg) => <span className="capitalize">{reg.role_type}</span>,
    },
    {
      key: 'registered',
      header: 'Requested on',
      cell: (reg) => formatDate(reg.registered_at),
    },
    {
      key: 'status',
      header: 'Status',
      cell: (reg) => <StatusBadge kind="registration" status={reg.status} />,
    },
    {
      key: 'actions',
      header: <span className="sr-only">Actions</span>,
      className: 'text-right',
      cell: (reg) =>
        reg.status === 'pending' ? (
          <div className="flex justify-end gap-1.5">
            <Button
              size="sm"
              variant="outline"
              onClick={() => setPendingAction({ kind: 'accept', registration: reg })}
            >
              Accept
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="text-status-rejected hover:text-status-rejected"
              onClick={() => setPendingAction({ kind: 'reject', registration: reg })}
            >
              Reject
            </Button>
          </div>
        ) : null,
    },
  ];

  const selectedCount = pendingRows.filter((reg) => selected.has(reg.id)).length;

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <FilterTabs
          options={STATUS_TABS}
          value={status}
          label="Filter by status"
          onChange={(value) => {
            setStatus(value);
            setPage(1);
            setSelected(new Set());
          }}
        />
        {selectedCount > 0 && (
          <div className="flex items-center gap-2" role="toolbar" aria-label="Bulk actions">
            <span className="text-sm text-muted-foreground tabular-nums">
              {bulk
                ? `${bulk.kind === 'accept' ? 'Accepting' : 'Rejecting'} ${bulk.done}/${bulk.total}…`
                : `${selectedCount} selected`}
            </span>
            <Button size="sm" disabled={!!bulk} onClick={() => runBulk('accept')}>
              Accept ({selectedCount})
            </Button>
            <Button size="sm" variant="destructive" disabled={!!bulk} onClick={() => runBulk('reject')}>
              Reject ({selectedCount})
            </Button>
          </div>
        )}
      </div>

      <DataTable
        columns={columns}
        rows={rows}
        rowKey={(reg) => reg.id}
        loading={isPending}
        caption="Event registrations"
        emptyState={
          <EmptyState
            icon={UsersRound}
            title={status === 'pending' ? 'No pending requests' : 'No registrations'}
            description={
              status === 'pending'
                ? 'New join requests appear here for review.'
                : 'Registrations appear once students join this event.'
            }
          />
        }
      />
      {data && <Paginator meta={data} onPageChange={setPage} />}

      <ConfirmDialog
        open={!!pendingAction}
        onOpenChange={(open) => !open && setPendingAction(null)}
        title={
          pendingAction?.kind === 'accept'
            ? `Accept ${pendingAction.registration.student?.name ?? 'this registration'}?`
            : `Reject ${pendingAction?.registration.student?.name ?? 'this registration'}?`
        }
        description="The student will be notified."
        confirmLabel={pendingAction?.kind === 'accept' ? 'Accept' : 'Reject'}
        destructive={pendingAction?.kind === 'reject'}
        pending={rowBusy}
        onConfirm={runSingle}
      />
    </div>
  );
}
