import { ActionIcon, Checkbox, Text } from '@mantine/core';
import { IconDotsVertical, IconFolder } from '@tabler/icons-react';
import { createColumnHelper } from '@tanstack/react-table';
import { formatDistanceToNow } from 'date-fns';
import { dirname } from 'pathe';

import { RowActions } from './RowActions';
import {
  GeneratorStatus,
  GeneratorsInfo,
} from '@/api/routes/generators/schemas';
import { RecordNameLink } from '@/components/ui/RecordNameLink';
import { StatusPill } from '@/components/ui/StatusPill';
import { ROUTE_PATHS } from '@/routing/paths';

// Base instance info enriched with per-instance runtime stats. Stats are
// available only for running instances; the rest carry `undefined` and
// render "-" (and sort last).
export type InstanceRow = GeneratorsInfo[number] & {
  flow: number | undefined;
  cpu: number | undefined;
  errors: number | undefined;
  written: number | undefined;
};

const columnHelper = createColumnHelper<InstanceRow>();

function rankInstanceStatus(status: GeneratorStatus): number {
  if (status.is_initializing) return 1;
  if (status.is_stopping) return 2;
  if (status.is_running) return 3;
  if (status.is_ended_up_successfully) return 4;
  if (status.is_ended_up) return 5;

  return 999;
}

const compactNumber = new Intl.NumberFormat('en', {
  notation: 'compact',
  maximumFractionDigits: 1,
});

const noData = (
  <Text span c="dimmed" size="sm">
    -
  </Text>
);

export const columns = [
  columnHelper.display({
    id: 'select',
    header: ({ table }) => (
      <Checkbox
        size="xs"
        title="Select all"
        checked={table.getIsAllPageRowsSelected()}
        indeterminate={table.getIsSomePageRowsSelected()}
        onChange={(e) =>
          table.toggleAllPageRowsSelected(e.currentTarget.checked)
        }
      />
    ),
    cell: ({ row }) => {
      return (
        <Checkbox
          size="xs"
          checked={row.getIsSelected()}
          onChange={(e) => {
            row.toggleSelected(e.currentTarget.checked);
          }}
        />
      );
    },
    meta: {
      style: { width: '1%', whiteSpace: 'nowrap' },
    },
  }),
  columnHelper.accessor('id', {
    header: 'Instance',
    id: 'id',
    enableSorting: true,
    enableColumnFilter: true,
    cell: (info) => (
      <RecordNameLink to={`${ROUTE_PATHS.INSTANCES}/${info.getValue()}`}>
        {info.getValue()}
      </RecordNameLink>
    ),
  }),
  columnHelper.accessor('path', {
    header: 'Project',
    id: 'path',
    enableSorting: true,
    enableColumnFilter: true,
    filterFn: (row, columnId, filterValue: string) => {
      const rowValue: string = row.getValue(columnId);
      const projectName = dirname(rowValue);
      return projectName.includes(filterValue);
    },
    cell: (info) => {
      const projectName = dirname(info.getValue());
      return (
        <RecordNameLink to={`${ROUTE_PATHS.PROJECTS}/${projectName}`}>
          <span
            style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}
            title="Go to project"
          >
            <IconFolder size={14} style={{ flexShrink: 0 }} />
            {projectName}
          </span>
        </RecordNameLink>
      );
    },
  }),
  columnHelper.accessor('status', {
    header: 'Status',
    id: 'status',
    enableColumnFilter: true,
    filterFn: (row, columnId, filterValue: boolean) => {
      const rowValue: GeneratorStatus = row.getValue(columnId);

      if (!filterValue) {
        return true;
      }

      return rowValue.is_running;
    },
    sortingFn: (rowA, rowB, columnId) => {
      const rowValueA: GeneratorStatus = rowA.getValue(columnId);
      const rowValueB: GeneratorStatus = rowB.getValue(columnId);

      return rankInstanceStatus(rowValueA) - rankInstanceStatus(rowValueB);
    },
    cell: (info) => <StatusPill status={info.getValue()} />,
  }),
  columnHelper.accessor('flow', {
    header: 'Flow',
    id: 'flow',
    enableSorting: true,
    sortUndefined: 'last',
    cell: (info) => {
      const value = info.getValue();

      if (value === undefined) {
        return noData;
      }

      return (
        <Text span size="sm" style={{ fontVariantNumeric: 'tabular-nums' }}>
          {value.toFixed(2)}
          <Text span c="dimmed" size="xs">
            {' '}
            eps
          </Text>
        </Text>
      );
    },
  }),
  columnHelper.accessor('cpu', {
    header: 'CPU',
    id: 'cpu',
    enableSorting: true,
    sortUndefined: 'last',
    cell: (info) => {
      const value = info.getValue();

      if (value === undefined) {
        return noData;
      }

      return (
        <Text
          span
          size="sm"
          style={{ fontVariantNumeric: 'tabular-nums' }}
          title="Average share of one core since the instance started"
        >
          {value.toFixed(1)}
          <Text span c="dimmed" size="xs">
            {' '}
            %
          </Text>
        </Text>
      );
    },
  }),
  columnHelper.accessor('errors', {
    header: 'Errors',
    id: 'errors',
    enableSorting: true,
    sortUndefined: 'last',
    cell: (info) => {
      const value = info.getValue();

      if (value === undefined) {
        return noData;
      }

      return (
        <Text
          span
          size="sm"
          style={{
            fontVariantNumeric: 'tabular-nums',
            color: value > 0 ? 'var(--mantine-color-red-text)' : undefined,
            fontWeight: value > 0 ? 600 : undefined,
          }}
        >
          {compactNumber.format(value)}
        </Text>
      );
    },
  }),
  columnHelper.accessor('written', {
    header: 'Written',
    id: 'written',
    enableSorting: true,
    sortUndefined: 'last',
    cell: (info) => {
      const value = info.getValue();

      if (value === undefined) {
        return noData;
      }

      return (
        <Text span size="sm" style={{ fontVariantNumeric: 'tabular-nums' }}>
          {compactNumber.format(value)}
        </Text>
      );
    },
  }),
  columnHelper.accessor('start_time', {
    header: 'Last start time',
    id: 'start_time',
    enableSorting: true,
    cell: (info) => {
      const lastStarted = info.getValue();

      if (lastStarted === null) {
        return <>-</>;
      }

      return (
        <>
          {formatDistanceToNow(Date.parse(lastStarted), {
            addSuffix: true,
            includeSeconds: true,
          })}
        </>
      );
    },
    meta: {
      style: { width: '15%' },
    },
  }),
  columnHelper.display({
    id: 'actions',
    cell: ({ row, table }) => {
      const original = row.original;
      const existingInstanceIds = table.options.data.map(
        (instance) => instance.id
      );
      return (
        <RowActions
          target={
            <ActionIcon variant="transparent">
              <IconDotsVertical size={20} />
            </ActionIcon>
          }
          instanceId={original.id}
          instanceStatus={original.status}
          existingInstanceIds={existingInstanceIds}
        />
      );
    },
    meta: {
      style: { width: '1%', whiteSpace: 'nowrap' },
    },
  }),
];
