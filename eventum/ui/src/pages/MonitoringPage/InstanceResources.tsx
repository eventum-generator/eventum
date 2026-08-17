import { Center, Paper, Stack, Table, Text } from '@mantine/core';
import bytes from 'bytes';
import { FC, useMemo } from 'react';

import { SectionLabel } from './SectionLabel';
import { formatRate } from './format';
import { InstanceUsageRow, UsagePoint, instanceUsageRows } from './history';
import { CPU_THRESHOLDS, levelColor } from '@/utils/levelColor';

/** Share of one core, coloured by the same thresholds as the host reading. */
const Share: FC<{ percent: number }> = ({ percent }) => (
  <Text
    size="sm"
    ff="monospace"
    fw={700}
    c={levelColor(percent, CPU_THRESHOLDS.warn, CPU_THRESHOLDS.bad)}
    style={{ fontVariantNumeric: 'tabular-nums' }}
  >
    {percent.toFixed(1)}%
  </Text>
);

const Figure: FC<{ children: string }> = ({ children }) => (
  <Text size="sm" ff="monospace" style={{ fontVariantNumeric: 'tabular-nums' }}>
    {children}
  </Text>
);

function queueLabel(row: InstanceUsageRow): string {
  const held = bytes(row.queueBytes, { decimalPlaces: 1 }) ?? '0B';
  if (row.queueMaxBytes === null) return held;

  return `${held} / ${bytes(row.queueMaxBytes, { decimalPlaces: 0 }) ?? '0B'}`;
}

interface InstanceResourcesProps {
  usage: UsagePoint[];
}

/**
 * What each running instance costs the host, heaviest first. The page already
 * shows how much each of them produces; this is the other half of the same
 * question - which instance to stop when the host runs hot, and whether an
 * instance is slow of its own accord or waiting for a processor the others
 * are using.
 */
export const InstanceResources: FC<InstanceResourcesProps> = ({ usage }) => {
  const rows = useMemo(() => instanceUsageRows(usage), [usage]);

  return (
    <Stack gap="xs">
      <SectionLabel>Instance resources</SectionLabel>
      <Paper withBorder p="md">
        {rows.length === 0 ? (
          <Center h={120}>
            <Text size="sm" c="dimmed">
              Collecting data...
            </Text>
          </Center>
        ) : (
          <Table
            highlightOnHover
            verticalSpacing="xs"
            horizontalSpacing="md"
            layout="auto"
          >
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Instance</Table.Th>
                <Table.Th>CPU</Table.Th>
                <Table.Th>Wait</Table.Th>
                <Table.Th>Threads</Table.Th>
                <Table.Th>Disk write</Table.Th>
                <Table.Th>Network out</Table.Th>
                <Table.Th>Events queue</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {rows.map((row) => (
                <Table.Tr key={row.id}>
                  <Table.Td>
                    <Text size="sm" fw={500} truncate maw={200}>
                      {row.id}
                    </Text>
                  </Table.Td>
                  <Table.Td>
                    <Share percent={row.cpuPercent} />
                  </Table.Td>
                  <Table.Td>
                    <Share percent={row.waitPercent} />
                  </Table.Td>
                  <Table.Td>
                    <Figure>{String(row.threads)}</Figure>
                  </Table.Td>
                  <Table.Td>
                    <Figure>{formatRate(row.diskWriteBps)}</Figure>
                  </Table.Td>
                  <Table.Td>
                    <Figure>{formatRate(row.netSentBps)}</Figure>
                  </Table.Td>
                  <Table.Td>
                    <Figure>{queueLabel(row)}</Figure>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        )}
      </Paper>
    </Stack>
  );
};
