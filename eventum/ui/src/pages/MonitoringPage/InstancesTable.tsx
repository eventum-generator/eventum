import { ActionIcon, Box, Group, Table, Text } from '@mantine/core';
import {
  IconArrowsSort,
  IconSortAscending,
  IconSortDescending,
} from '@tabler/icons-react';
import bytes from 'bytes';
import { FC, useMemo, useState } from 'react';

import { formatEps, formatRate } from './format';
import { InstanceUsageRow } from './history';
import { FALLBACK_COLOR } from './instanceColors';
import {
  CPU_THRESHOLDS,
  QUEUE_THRESHOLDS,
  levelColor,
} from '@/utils/levelColor';

type SortKey =
  | 'id'
  | 'cpuPercent'
  | 'waitPercent'
  | 'outputEps'
  | 'failEps'
  | 'diskWriteBps'
  | 'netSentBps'
  | 'queuePercent'
  | 'threads';

interface Column {
  key: SortKey;
  label: string;
  /** Ascending is the natural first click for names, descending for load. */
  ascFirst?: boolean;
}

const COLUMNS: Column[] = [
  { key: 'id', label: 'Instance', ascFirst: true },
  { key: 'cpuPercent', label: 'CPU' },
  { key: 'waitPercent', label: 'Wait' },
  { key: 'outputEps', label: 'Output' },
  { key: 'failEps', label: 'Failures' },
  { key: 'diskWriteBps', label: 'Disk write' },
  { key: 'netSentBps', label: 'Network out' },
  { key: 'queuePercent', label: 'Events queue' },
  { key: 'threads', label: 'Threads' },
];

const Figure: FC<{ children: string; color?: string }> = ({
  children,
  color,
}) => (
  <Text
    size="sm"
    ff="monospace"
    c={color}
    fw={color ? 700 : undefined}
    style={{ fontVariantNumeric: 'tabular-nums' }}
  >
    {children}
  </Text>
);

const formatBytes = (value: number) =>
  bytes(value, { decimalPlaces: 1 }) ?? '0B';

function queueLabel(row: InstanceUsageRow): string {
  const held = formatBytes(row.queueBytes);
  if (row.queueMaxBytes === null) return held;
  return `${held} / ${formatBytes(row.queueMaxBytes)}`;
}

function compare(a: InstanceUsageRow, b: InstanceUsageRow, key: SortKey) {
  if (key === 'id') return a.id.localeCompare(b.id);
  return a[key] - b[key];
}

interface InstancesTableProps {
  rows: InstanceUsageRow[];
  colorOf: Map<string, string>;
  selectedId: string | null;
  onSelect: (id: string) => void;
}

/**
 * What each running instance costs the host, sortable by every figure it
 * shows. The swatch ties a row to its band in the chart above, and selecting
 * a row opens its details beside the table.
 */
export const InstancesTable: FC<InstancesTableProps> = ({
  rows,
  colorOf,
  selectedId,
  onSelect,
}) => {
  const [sort, setSort] = useState<{ key: SortKey; desc: boolean }>({
    key: 'cpuPercent',
    desc: true,
  });

  const sorted = useMemo(() => {
    const direction = sort.desc ? -1 : 1;
    return [...rows].sort((a, b) => direction * compare(a, b, sort.key));
  }, [rows, sort]);

  function toggle(column: Column) {
    setSort((current) =>
      current.key === column.key
        ? { key: column.key, desc: !current.desc }
        : { key: column.key, desc: !column.ascFirst }
    );
  }

  return (
    <Table.ScrollContainer minWidth={860}>
      <Table highlightOnHover verticalSpacing="xs" horizontalSpacing="md">
        <Table.Thead>
          <Table.Tr>
            {COLUMNS.map((column) => {
              const active = sort.key === column.key;
              const Icon = !active
                ? IconArrowsSort
                : sort.desc
                  ? IconSortAscending
                  : IconSortDescending;

              return (
                <Table.Th key={column.key}>
                  <Group gap={4} wrap="nowrap">
                    {column.label}
                    <ActionIcon
                      variant="transparent"
                      size="sm"
                      c={active ? undefined : 'dimmed'}
                      onClick={() => toggle(column)}
                      aria-label={`Sort by ${column.label}`}
                    >
                      <Icon size={15} />
                    </ActionIcon>
                  </Group>
                </Table.Th>
              );
            })}
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {sorted.map((row) => (
            <Table.Tr
              key={row.id}
              onClick={() => onSelect(row.id)}
              bg={
                row.id === selectedId
                  ? 'var(--mantine-color-default-hover)'
                  : undefined
              }
              style={{ cursor: 'pointer' }}
            >
              <Table.Td>
                <Group gap={8} wrap="nowrap">
                  <Box
                    style={{
                      width: 10,
                      height: 10,
                      borderRadius: 3,
                      background: colorOf.get(row.id) ?? FALLBACK_COLOR,
                      flexShrink: 0,
                    }}
                  />
                  <Text size="sm" fw={500} truncate maw={220}>
                    {row.id}
                  </Text>
                </Group>
              </Table.Td>
              <Table.Td>
                <Figure
                  color={levelColor(
                    row.cpuPercent,
                    CPU_THRESHOLDS.warn,
                    CPU_THRESHOLDS.bad
                  )}
                >
                  {`${row.cpuPercent.toFixed(1)}%`}
                </Figure>
              </Table.Td>
              <Table.Td>
                <Figure
                  color={levelColor(
                    row.waitPercent,
                    CPU_THRESHOLDS.warn,
                    CPU_THRESHOLDS.bad
                  )}
                >
                  {`${row.waitPercent.toFixed(1)}%`}
                </Figure>
              </Table.Td>
              <Table.Td>
                <Figure>{`${formatEps(row.outputEps)}/s`}</Figure>
              </Table.Td>
              <Table.Td>
                <Figure
                  color={
                    row.failEps > 0
                      ? 'var(--mantine-color-red-text)'
                      : undefined
                  }
                >
                  {`${formatEps(row.failEps)}/s`}
                </Figure>
              </Table.Td>
              <Table.Td>
                <Figure>{formatRate(row.diskWriteBps)}</Figure>
              </Table.Td>
              <Table.Td>
                <Figure>{formatRate(row.netSentBps)}</Figure>
              </Table.Td>
              <Table.Td>
                <Group gap={8} wrap="nowrap">
                  <Figure
                    color={levelColor(
                      row.queuePercent,
                      QUEUE_THRESHOLDS.warn,
                      QUEUE_THRESHOLDS.bad
                    )}
                  >
                    {`${Math.round(row.queuePercent)}%`}
                  </Figure>
                  <Text size="xs" c="dimmed" ff="monospace">
                    {queueLabel(row)}
                  </Text>
                </Group>
              </Table.Td>
              <Table.Td>
                <Figure>{String(row.threads)}</Figure>
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Table.ScrollContainer>
  );
};
