import { Ticket } from 'lucide-react';
import { Link, useSearchParams } from 'react-router-dom';
import { DataTable, type Column } from '@/components/common/DataTable';
import { EmptyState } from '@/components/common/EmptyState';
import { PageHeader } from '@/components/common/PageHeader';
import { Paginator } from '@/components/common/Paginator';
import { StatusBadge } from '@/components/common/StatusBadge';
import { FilterTabs } from '@/components/common/FilterTabs';
import { useMyRegistrations } from '@/hooks/useRegistrations';
import { formatDate, formatDateRange } from '@/lib/format';
import type { Registration } from '@/types/domain';
import type { RegistrationRole, RegistrationStatus } from '@/types/enums';

const STATUS_TABS = ['all', 'pending', 'accepted', 'rejected'] as const;

const COPY: Record<RegistrationRole, { title: string; description: string; empty: string }> = {
  participant: {
    title: 'Participation',
    description: 'Events you asked to take part in.',
    empty: 'Browse events and join one as a participant — your requests land here.',
  },
  volunteer: {
    title: 'Volunteering',
    description: 'Events you offered to help run.',
    empty: 'Browse events and join one as a volunteer — your requests land here.',
  },
};

export function MyRegistrationsPage({ roleType }: { roleType: RegistrationRole }) {
  const [searchParams, setSearchParams] = useSearchParams();
  const statusParam = searchParams.get('status');
  const status = (STATUS_TABS as readonly string[]).includes(statusParam ?? '')
    ? (statusParam as (typeof STATUS_TABS)[number])
    : 'all';
  const page = Number(searchParams.get('page')) || 1;

  const { data, isPending } = useMyRegistrations({
    page,
    limit: 100,
    status: status === 'all' ? undefined : (status as RegistrationStatus),
  });

  const rows = (data?.items ?? []).filter((reg) => reg.role_type === roleType);

  const columns: Column<Registration>[] = [
    {
      key: 'event',
      header: 'Event',
      cell: (reg) =>
        reg.event ? (
          <Link
            to={`/student/events/${reg.event.id}`}
            className="font-medium underline-offset-4 hover:underline"
          >
            {reg.event.title}
          </Link>
        ) : (
          '—'
        ),
    },
    {
      key: 'dates',
      header: 'Event dates',
      cell: (reg) => (reg.event ? formatDateRange(reg.event.start_date, reg.event.end_date) : '—'),
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
  ];

  return (
    <div>
      <PageHeader title={COPY[roleType].title} description={COPY[roleType].description} />
      <div className="mb-4">
        <FilterTabs
          options={STATUS_TABS}
          value={status}
          label="Filter by status"
          onChange={(value) =>
            setSearchParams((prev) => {
              const next = new URLSearchParams(prev);
              if (value === 'all') next.delete('status');
              else next.set('status', value);
              next.delete('page');
              return next;
            })
          }
        />
      </div>

      <DataTable
        columns={columns}
        rows={rows}
        rowKey={(reg) => reg.id}
        loading={isPending}
        caption={`${COPY[roleType].title} requests`}
        emptyState={
          <EmptyState icon={Ticket} title="Nothing here yet" description={COPY[roleType].empty} />
        }
      />
      {data && (
        <Paginator
          meta={data}
          onPageChange={(next) =>
            setSearchParams((prev) => {
              const params = new URLSearchParams(prev);
              params.set('page', String(next));
              return params;
            })
          }
        />
      )}
    </div>
  );
}
