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
import { FC, useEffect, useMemo, useState } from 'react';

import { InstanceRow, columns } from './columns';
import {
  GeneratorStats,
  GeneratorsInfo,
} from '@/api/routes/generators/schemas';

export type StatusMode = 'all' | 'active' | 'inactive';

/** Total pipeline errors: produce, write and format failures (drops,
 *  being intentional, are not counted). */
function countErrors(stats: GeneratorStats): number {
  const outputFailed = stats.output.reduce(
    (sum, plugin) => sum + plugin.write_failed + plugin.format_failed,
    0
  );

  return stats.event.produce_failed + outputFailed;
}

/**
 * Share of one core an instance has taken on average since it started. The
 * list is fetched once rather than polled, so there is no earlier sample to
 * derive the share at this moment from - the Monitoring page does that.
 */
function averageCpuShare(stats: GeneratorStats): number | undefined {
  if (stats.uptime <= 0) {
    return undefined;
  }

  return (stats.resources.cpu_seconds / stats.uptime) * 100;
}

interface InstancesTableProps {
  data: GeneratorsInfo;
  instancesFilter?: string;
  projectNameFilter?: string;
  statusMode?: StatusMode;
  statsById?: Record<string, GeneratorStats>;
  rowSelection: RowSelectionState;
  onRowSelectionChange: React.Dispatch<React.SetStateAction<RowSelectionState>>;
}

/**
 * The name of the control that sorts a column.
 *
 * The control is an icon alone, so it carries the name of the column it
 * sorts - the header of that column when it is a word rather than a
 * component of its own.
 */
function sortLabel(column: { id: string; columnDef: { header?: unknown } }) {
  const header = column.columnDef.header;

  return `Sort by ${typeof header === 'string' ? header.toLowerCase() : column.id}`;
}

export const InstancesTable: FC<InstancesTableProps> = ({
  data,
  projectNameFilter = '',
  instancesFilter = '',
  statusMode = 'all',
  statsById,
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

  // Status filtering runs here rather than through a column filter so it
  // stays out of columns.tsx. "active" keeps live and transitioning
  // instances; "inactive" keeps every instance at rest (idle, finished,
  // failed).
  const statusFilteredData = useMemo(() => {
    if (statusMode === 'all') {
      return data;
    }

    return data.filter((instance) => {
      const isLive =
        instance.status.is_running ||
        instance.status.is_initializing ||
        instance.status.is_stopping;

      return statusMode === 'active' ? isLive : !isLive;
    });
  }, [data, statusMode]);

  // Enrich each row with its runtime stats so Flow/Errors/Written are real
  // columns (sortable). Non-running instances have no stats -> undefined.
  const rows = useMemo<InstanceRow[]>(
    () =>
      statusFilteredData.map((instance) => {
        const stats = statsById?.[instance.id];

        return {
          ...instance,
          flow: stats ? stats.output_eps : undefined,
          cpu: stats ? averageCpuShare(stats) : undefined,
          errors: stats ? countErrors(stats) : undefined,
          written: stats ? stats.total_written : undefined,
        };
      }),
    [statusFilteredData, statsById]
  );

  const table = useReactTable({
    data: rows,
    columns,
    getRowId: (instance) => instance.id,
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
  }, [instancesFilter, projectNameFilter, table]);

  return (
    <Stack>
      <Paper withBorder p="sm">
        {/* Eight columns do not compress below ~900px, and without a scroll
            container of its own the table widens the document instead - the
            rightmost columns, the row menu among them, end up off-screen with
            only the page scrollbar to reach them. `type="native"` keeps the
            platform scrollbar and touch scrolling; Mantine's default
            ScrollArea replaces both. */}
        <Table.ScrollContainer minWidth={900} type="native">
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
                                    aria-label={sortLabel(header.column)}
                                    onClick={header.column.getToggleSortingHandler()}
                                  >
                                    <IconSortDescending size={16} />
                                  </ActionIcon>
                                )}
                                {header.column.getIsSorted() === 'desc' && (
                                  <ActionIcon
                                    variant="transparent"
                                    size="sm"
                                    aria-label={sortLabel(header.column)}
                                    onClick={header.column.getToggleSortingHandler()}
                                  >
                                    <IconSortAscending size={16} />
                                  </ActionIcon>
                                )}
                                {header.column.getIsSorted() === false && (
                                  <ActionIcon
                                    variant="transparent"
                                    size="sm"
                                    aria-label={sortLabel(header.column)}
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
                      {flexRender(
                        cell.column.columnDef.cell,
                        cell.getContext()
                      )}
                    </Table.Td>
                  ))}
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
        {table.getFilteredRowModel().rows.length === 0 && (
          <Center mt="xs">
            <Text size="sm" c="dimmed">
              No instances match your filters
            </Text>
          </Center>
        )}
      </Paper>

      {table.getFilteredRowModel().rows.length > 0 && (
        <Group w="100%" justify="end" gap="lg">
          <Text size="sm" c="dimmed">
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
            <Text size="sm" c="dimmed">
              Page size:
            </Text>

            <Select
              data={['10', '15', '25', '50', '100']}
              size="sm"
              w={68}
              variant="unstyled"
              styles={{ input: { textAlign: 'center' } }}
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
