import { ActionIcon } from '@mantine/core';
import { IconDotsVertical } from '@tabler/icons-react';
import { createColumnHelper } from '@tanstack/react-table';

import { RowActions } from './RowActions';
import { StatusBadges } from './StatusBadges';
import { ScenarioRow } from './types';

const columnHelper = createColumnHelper<ScenarioRow>();

export function createColumns() {
  return [
    columnHelper.accessor('name', {
      header: 'Name',
      id: 'name',
      enableSorting: true,
      enableColumnFilter: true,
      cell: (info) => info.getValue(),
    }),
    columnHelper.accessor('generatorCount', {
      header: 'Generators',
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
          />
        );
      },
      meta: {
        style: { width: '1%', whiteSpace: 'nowrap' },
      },
    }),
  ];
}
