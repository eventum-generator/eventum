import { ActionIcon, Checkbox, Group, Indicator, Text } from '@mantine/core';
import { IconDotsVertical } from '@tabler/icons-react';
import { createColumnHelper } from '@tanstack/react-table';
import { formatDistanceToNow } from 'date-fns';
import { dirname } from 'pathe';

import { RowActions } from './RowActions';
import { describeInstanceStatus } from './common/instance-status';
import {
  GeneratorStatus,
  GeneratorsInfo,
} from '@/api/routes/generators/schemas';

const columnHelper = createColumnHelper<GeneratorsInfo[number]>();

function rankInstanceStatus(status: GeneratorStatus): number {
  if (status.is_initializing) return 1;
  if (status.is_stopping) return 2;
  if (status.is_running) return 3;
  if (status.is_ended_up_successfully) return 4;
  if (status.is_ended_up) return 5;

  return 999;
}

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
    cell: (info) => info.getValue(),
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
    cell: (info) => dirname(info.getValue()),
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
    cell: (info) => {
      const status = info.getValue();

      const { text, color, processing } = describeInstanceStatus(status);

      return (
        <Group gap="sm" align="center">
          <Indicator
            color={color}
            size={8}
            position="middle-center"
            processing={processing}
          />
          <Text size="sm">{text}</Text>
        </Group>
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
      style: { width: '20%' },
    },
  }),
  columnHelper.display({
    id: 'actions',
    cell: ({ row }) => {
      const original = row.original;
      return (
        <RowActions
          target={
            <ActionIcon variant="transparent">
              <IconDotsVertical size={20} />
            </ActionIcon>
          }
          instanceId={original.id}
          instanceStatus={original.status}
        />
      );
    },
    meta: {
      style: { width: '1%', whiteSpace: 'nowrap' },
    },
  }),
];
