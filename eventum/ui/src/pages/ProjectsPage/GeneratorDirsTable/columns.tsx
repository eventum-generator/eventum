import { ActionIcon } from '@mantine/core';
import { IconDotsVertical } from '@tabler/icons-react';
import { createColumnHelper } from '@tanstack/react-table';
import bytes from 'bytes';
import { formatDistanceToNow } from 'date-fns';

import { RowActions } from './RowActions';
import { GeneratorDirsExtendedInfo } from '@/api/routes/generator-configs/schemas';
import { InstanceBadges } from '@/components/ui/InstanceBadges';
import { RecordNameLink } from '@/components/ui/RecordNameLink';
import { ROUTE_PATHS } from '@/routing/paths';

const columnHelper = createColumnHelper<GeneratorDirsExtendedInfo[number]>();

export const columns = [
  columnHelper.accessor('name', {
    header: 'Project Name',
    id: 'name',
    enableSorting: true,
    enableColumnFilter: true,
    cell: (info) => (
      <RecordNameLink to={`${ROUTE_PATHS.PROJECTS}/${info.getValue()}`}>
        {info.getValue()}
      </RecordNameLink>
    ),
  }),
  columnHelper.accessor('generator_ids', {
    header: 'Instances',
    id: 'generator_ids',
    enableSorting: false,
    enableColumnFilter: true,
    filterFn: (
      row,
      columnId,
      filterValue: {
        instancesFilter: string[];
        usageMode: 'all' | 'used' | 'unused';
      }
    ) => {
      const rowValue: string[] = row.getValue(columnId);

      if (filterValue.usageMode === 'used' && rowValue.length === 0) {
        return false;
      }
      if (filterValue.usageMode === 'unused' && rowValue.length > 0) {
        return false;
      }

      if (filterValue.instancesFilter.length === 0) return true;

      return filterValue.instancesFilter.some((selectedItem) =>
        rowValue.includes(selectedItem)
      );
    },
    cell: (info) => (
      <InstanceBadges
        ids={info.getValue()}
        moreTo={`${ROUTE_PATHS.INSTANCES}?project=${encodeURIComponent(
          info.row.original.name
        )}`}
      />
    ),
  }),
  columnHelper.accessor('last_modified', {
    header: 'Modified',
    id: 'last_modified',
    enableSorting: true,
    cell: (info) => {
      const lastModified = info.getValue();

      if (lastModified === null) {
        return <>-</>;
      }

      return (
        <>
          {formatDistanceToNow(new Date(lastModified * 1000), {
            addSuffix: true,
            includeSeconds: true,
          })}
        </>
      );
    },
  }),
  columnHelper.accessor('size_in_bytes', {
    header: 'Size',
    id: 'size_in_bytes',
    enableSorting: true,
    cell: (info) => {
      const sizeInBytes = info.getValue();

      if (sizeInBytes === null) {
        return <>-</>;
      }

      return <>{bytes(sizeInBytes)}</>;
    },
  }),
  columnHelper.display({
    id: 'actions',
    cell: ({ row }) => {
      const original = row.original;
      return (
        <RowActions
          target={
            <ActionIcon variant="transparent" aria-label="Project actions">
              <IconDotsVertical size={20} />
            </ActionIcon>
          }
          dirName={original.name}
          generatorIds={original.generator_ids}
        />
      );
    },
    meta: {
      style: { width: '1%', whiteSpace: 'nowrap' }, // custom style
    },
  }),
];
