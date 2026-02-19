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
import { GeneratorDirsExtendedInfo } from '@/api/routes/generator-configs/schemas';

interface GeneratorDirsTableProps {
  data: GeneratorDirsExtendedInfo;
  projectNameFilter?: string;
  instancesFilter?: string[];
  anyInstanceFilter?: boolean;
}

export const GeneratorDirsTable: FC<GeneratorDirsTableProps> = ({
  data,
  projectNameFilter = '',
  instancesFilter = [],
  anyInstanceFilter = false,
}) => {
  const [sorting, setSorting] = useState<SortingState>([
    { id: 'name', desc: false },
  ]);
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);
  const [pagination, setPagination] = useState<PaginationState>({
    pageIndex: 0,
    pageSize: 15,
  });

  const table = useReactTable({
    data,
    columns,
    state: { sorting, columnFilters, pagination },
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onPaginationChange: setPagination,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
  });

  useEffect(() => {
    table.getColumn('name')?.setFilterValue(projectNameFilter);
    table.getColumn('generator_ids')?.setFilterValue({
      instancesFilter: instancesFilter,
      anyInstanceFilter: anyInstanceFilter,
    });
  }, [projectNameFilter, instancesFilter, anyInstanceFilter, table]);

  return (
    <Stack>
      <Paper withBorder p="sm">
        <Table>
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
          <Center mt="xs">
            <Text size="sm" c="gray.6">
              No projects
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
