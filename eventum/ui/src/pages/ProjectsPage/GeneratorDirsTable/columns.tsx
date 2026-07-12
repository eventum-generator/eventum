import { ActionIcon, Badge, Group, Text } from '@mantine/core';
import { IconDotsVertical } from '@tabler/icons-react';
import { createColumnHelper } from '@tanstack/react-table';
import bytes from 'bytes';
import { formatDistanceToNow } from 'date-fns';

import { RowActions } from './RowActions';
import { GeneratorDirsExtendedInfo } from '@/api/routes/generator-configs/schemas';
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
      filterValue: { instancesFilter: string[]; anyInstanceFilter: boolean }
    ) => {
      const rowValue: string[] = row.getValue(columnId);

      if (filterValue.anyInstanceFilter) {
        return rowValue.length > 0;
      }

      if (filterValue.instancesFilter.length === 0) return true;

      return filterValue.instancesFilter.some((selectedItem) =>
        rowValue.includes(selectedItem)
      );
    },
    cell: (info) => {
      const generatorIds = info.getValue();

      if (generatorIds.length === 0) {
        return (
          <Text c="gray.6" size="sm">
            Not used
          </Text>
        );
      }

      return (
        <Group gap="xs">
          {generatorIds.map((generator_id) => (
            <Badge
              size="md"
              variant="default"
              key={generator_id}
              style={{ textTransform: 'initial' }}
            >
              <Text size="xs">{generator_id}</Text>
            </Badge>
          ))}
        </Group>
      );
    },
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
            <ActionIcon variant="transparent">
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
