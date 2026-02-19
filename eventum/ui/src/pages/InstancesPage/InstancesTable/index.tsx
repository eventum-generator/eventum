import {
  ActionIcon,
  Center,
  Group,
  Pagination,
  Paper,
  Select,
  Stack,
  Table,
  Text,
} from '@mantine/core';
import {
  IconArrowsSort,
  IconSortAscending,
  IconSortDescending,
} from '@tabler/icons-react';
import {
  ColumnFiltersState,
  PaginationState,
  RowSelectionState,
  SortingState,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
} from '@tanstack/react-table';
import { FC, useEffect, useState } from 'react';

import { columns } from './columns';
import { GeneratorsInfo } from '@/api/routes/generators/schemas';

interface InstancesTableProps {
  data: GeneratorsInfo;
  instancesFilter?: string;
  projectNameFilter?: string;
  runningOnlyFilter?: boolean;
  rowSelection: RowSelectionState;
  onRowSelectionChange: React.Dispatch<React.SetStateAction<RowSelectionState>>;
}

export const InstancesTable: FC<InstancesTableProps> = ({
  data,
  projectNameFilter = '',
  instancesFilter = '',
  runningOnlyFilter = false,
  rowSelection,
  onRowSelectionChange,
}) => {
  const [sorting, setSorting] = useState<SortingState>([
    { id: 'id', desc: false },
  ]);
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);
  const [pagination, setPagination] = useState<PaginationState>({
    pageIndex: 0,
    pageSize: 15,
  });

  const table = useReactTable({
    data,
    columns,
    state: { sorting, columnFilters, pagination, rowSelection },
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onPaginationChange: setPagination,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    enableRowSelection: true,
    onRowSelectionChange: onRowSelectionChange,
  });

  useEffect(() => {
    table.getColumn('id')?.setFilterValue(instancesFilter);
    table.getColumn('path')?.setFilterValue(projectNameFilter);
    table.getColumn('status')?.setFilterValue(runningOnlyFilter);
  }, [instancesFilter, projectNameFilter, runningOnlyFilter, table]);

  return (
    <Stack>
      <Paper withBorder p="sm">
        <Table bdrs="md">
          <Table.Thead>
            {table.getHeaderGroups().map((headerGroup) => (
              <Table.Tr key={headerGroup.id}>
                {headerGroup.headers.map((header) => {
                  const meta = header.column.columnDef?.meta as
                    | { style?: React.CSSProperties }
                    | undefined;

                  const style: React.CSSProperties = meta?.style ?? {};

                  return (
                    <Table.Th key={header.id} style={style}>
                      {header.isPlaceholder ? null : (
                        <Group gap="xs" wrap="nowrap">
                          {flexRender(
                            header.column.columnDef.header,
                            header.getContext()
                          )}

                          {header.column.getCanSort() && (
                            <>
                              {header.column.getIsSorted() === 'asc' && (
                                <ActionIcon
                                  variant="transparent"
                                  size="sm"
                                  onClick={header.column.getToggleSortingHandler()}
                                >
                                  <IconSortDescending size={16} />
                                </ActionIcon>
                              )}
                              {header.column.getIsSorted() === 'desc' && (
                                <ActionIcon
                                  variant="transparent"
                                  size="sm"
                                  onClick={header.column.getToggleSortingHandler()}
                                >
                                  <IconSortAscending size={16} />
                                </ActionIcon>
                              )}
                              {header.column.getIsSorted() === false && (
                                <ActionIcon
                                  variant="transparent"
                                  size="sm"
                                  onClick={header.column.getToggleSortingHandler()}
                                >
                                  <IconArrowsSort size={16} />
                                </ActionIcon>
                              )}
                            </>
                          )}
                        </Group>
                      )}
                    </Table.Th>
                  );
                })}
              </Table.Tr>
            ))}
          </Table.Thead>
          <Table.Tbody>
            {table.getRowModel().rows.map((row) => (
              <Table.Tr key={row.id}>
                {row.getVisibleCells().map((cell) => (
                  <Table.Td key={cell.id}>
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </Table.Td>
                ))}
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
        {data.length === 0 && (
          <Center mt="sm">
            <Text size="sm" c="gray.6">
              No instances
            </Text>
          </Center>
        )}
      </Paper>

      {data.length > 0 && (
        <Group w="100%" justify="end" gap="lg">
          <Text size="sm" c="gray.6">
            Showing{' '}
            {table.getState().pagination.pageIndex *
              table.getState().pagination.pageSize +
              1}{' '}
            -{' '}
            {Math.min(
              (table.getState().pagination.pageIndex + 1) *
                table.getState().pagination.pageSize,
              table.getFilteredRowModel().rows.length
            )}{' '}
            of {table.getFilteredRowModel().rows.length}
          </Text>
          <Group gap="xs">
            <Text size="sm" c="gray.6">
              Page size:
            </Text>

            <Select
              data={['10', '15', '25', '50', '100']}
              size="sm"
              w="60px"
              variant="unstyled"
              value={table.getState().pagination.pageSize.toString()}
              onChange={(value) =>
                table.setPageSize(Number.parseInt(value ?? '15'))
              }
              withCheckIcon={false}
            />
          </Group>
          <Pagination
            size="sm"
            total={table.getPageCount()}
            value={pagination.pageIndex + 1}
            onChange={(page) => {
              table.setPageIndex(page - 1);
            }}
          />
        </Group>
      )}
    </Stack>
  );
};
