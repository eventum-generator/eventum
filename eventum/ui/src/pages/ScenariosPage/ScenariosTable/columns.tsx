import { ActionIcon, Checkbox } from '@mantine/core';
import { IconDotsVertical } from '@tabler/icons-react';
import { createColumnHelper } from '@tanstack/react-table';

import { RowActions } from './RowActions';
import { StatusBadges } from './StatusBadges';
import { ScenarioRow } from './types';

const columnHelper = createColumnHelper<ScenarioRow>();

export function createColumns() {
  return [
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
      cell: ({ row }) => (
        <Checkbox
          size="xs"
          checked={row.getIsSelected()}
          onChange={(e) => row.toggleSelected(e.currentTarget.checked)}
        />
      ),
      meta: {
        style: { width: '1%', whiteSpace: 'nowrap' },
      },
    }),
    columnHelper.accessor('name', {
      header: 'Name',
      id: 'name',
      enableSorting: true,
      enableColumnFilter: true,
      cell: (info) => info.getValue(),
    }),
    columnHelper.accessor('generatorCount', {
      header: 'Instances',
      id: 'generatorCount',
      enableSorting: true,
      cell: (info) => info.getValue(),
    }),
    columnHelper.display({
      id: 'status',
      header: 'Status',
      cell: ({ row }) => <StatusBadges row={row.original} />,
    }),
    columnHelper.display({
      id: 'actions',
      cell: ({ row }) => {
        const original = row.original;
        return (
          <RowActions
            target={
              <ActionIcon variant="transparent" aria-label="Scenario actions">
                <IconDotsVertical size={20} />
              </ActionIcon>
            }
            scenarioName={original.name}
            generatorIds={original.generatorIds}
            hasRunning={original.runningCount > 0}
            hasInactive={original.stoppedCount > 0}
          />
        );
      },
      meta: {
        style: { width: '1%', whiteSpace: 'nowrap' },
      },
    }),
  ];
}
