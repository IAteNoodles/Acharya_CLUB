import { UsersRound } from 'lucide-react';
import { useState } from 'react';
import { toast } from 'sonner';
import { isApiError } from '@/api/errors';
import { ConfirmDialog } from '@/components/common/ConfirmDialog';
import { DataTable, type Column } from '@/components/common/DataTable';
import { EmptyState } from '@/components/common/EmptyState';
import { PageHeader } from '@/components/common/PageHeader';
import { Paginator } from '@/components/common/Paginator';
import { SearchInput } from '@/components/common/SearchInput';
import { StatusBadge } from '@/components/common/StatusBadge';
import { Button } from '@/components/ui/button';
import {
  useApproveTeacher,
  usePendingTeachers,
  useRejectTeacher,
  useTeachers,
} from '@/hooks/useUsers';
import { formatDate } from '@/lib/format';
import type { User } from '@/types/domain';

type PendingDecision = { kind: 'approve' | 'reject'; teacher: User } | null;

function PendingTeachersSection() {
  const [page, setPage] = useState(1);
  const [decision, setDecision] = useState<PendingDecision>(null);
  const { data, isPending } = usePendingTeachers({ page });
  const approve = useApproveTeacher();
  const reject = useRejectTeacher();
  const busy = approve.isPending || reject.isPending;

  const confirm = async () => {
    if (!decision) return;
    const action = decision.kind === 'approve' ? approve : reject;
    try {
      await action.mutateAsync(decision.teacher.id);
      toast.success(
        decision.kind === 'approve'
          ? `${decision.teacher.name} approved — they can sign in now.`
          : `${decision.teacher.name} rejected.`,
      );
    } catch (error) {
      toast.error(isApiError(error) ? error.message : 'Action failed. Try again.');
    } finally {
      setDecision(null);
    }
  };

  const columns: Column<User>[] = [
    {
      key: 'name',
      header: 'Name',
      cell: (teacher) => <span className="font-medium">{teacher.name}</span>,
    },
    { key: 'email', header: 'Email', cell: (teacher) => teacher.email },
    {
      key: 'registered',
      header: 'Registered',
      cell: (teacher) => (teacher.created_at ? formatDate(teacher.created_at) : '—'),
    },
    {
      key: 'actions',
      header: <span className="sr-only">Actions</span>,
      className: 'text-right',
      cell: (teacher) => (
        <div className="flex justify-end gap-1.5">
          <Button size="sm" onClick={() => setDecision({ kind: 'approve', teacher })}>
            Approve
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="text-status-rejected hover:text-status-rejected"
            onClick={() => setDecision({ kind: 'reject', teacher })}
          >
            Reject
          </Button>
        </div>
      ),
    },
  ];

  return (
    <section aria-labelledby="pending-teachers-heading">
      <h2 id="pending-teachers-heading" className="mb-3 text-lg font-semibold">
        Pending teacher accounts
        {data && data.total > 0 && (
          <span className="ml-2 align-middle">
            <StatusBadge kind="user" status="pending" />
          </span>
        )}
      </h2>
      <DataTable
        columns={columns}
        rows={data?.items ?? []}
        rowKey={(teacher) => teacher.id}
        loading={isPending}
        caption="Pending teacher accounts"
        emptyState={
          <EmptyState
            icon={UsersRound}
            title="No pending teachers"
            description="New teacher signups wait here for your approval."
          />
        }
      />
      {data && <Paginator meta={data} onPageChange={setPage} />}

      <ConfirmDialog
        open={!!decision}
        onOpenChange={(open) => !open && setDecision(null)}
        title={
          decision?.kind === 'approve'
            ? `Approve ${decision.teacher.name}?`
            : `Reject ${decision?.teacher.name}?`
        }
        description={
          decision?.kind === 'approve'
            ? 'They will be notified and can sign in immediately.'
            : 'They will be notified and will not be able to sign in.'
        }
        confirmLabel={decision?.kind === 'approve' ? 'Approve' : 'Reject'}
        destructive={decision?.kind === 'reject'}
        pending={busy}
        onConfirm={confirm}
      />
    </section>
  );
}

function TeacherDirectorySection() {
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const { data, isPending } = useTeachers({ search, page });

  const columns: Column<User>[] = [
    {
      key: 'name',
      header: 'Name',
      cell: (teacher) => <span className="font-medium">{teacher.name}</span>,
    },
    { key: 'email', header: 'Email', cell: (teacher) => teacher.email },
    {
      key: 'status',
      header: 'Status',
      cell: (teacher) => <StatusBadge kind="user" status={teacher.status} />,
    },
  ];

  return (
    <section aria-labelledby="teacher-directory-heading" className="mt-8">
      <h2 id="teacher-directory-heading" className="mb-3 text-lg font-semibold">
        Teacher directory
      </h2>
      <div className="mb-3 sm:w-64">
        <SearchInput
          value={search}
          onDebouncedChange={(value) => {
            setSearch(value);
            setPage(1);
          }}
          placeholder="Search teachers…"
          label="Search teachers"
        />
      </div>
      <DataTable
        columns={columns}
        rows={data?.items ?? []}
        rowKey={(teacher) => teacher.id}
        loading={isPending}
        caption="Active teachers"
        emptyState={
          <EmptyState
            icon={UsersRound}
            title="No teachers found"
            description="Approved teachers appear here and can be assigned as coordinators."
          />
        }
      />
      {data && <Paginator meta={data} onPageChange={setPage} />}
    </section>
  );
}

export function AdminPanelPage() {
  return (
    <div>
      <PageHeader
        title="Admin Panel"
        description="Approve teacher accounts and browse the teacher directory."
      />
      <PendingTeachersSection />
      <TeacherDirectorySection />
    </div>
  );
}
