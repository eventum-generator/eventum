import { Box, Group, Paper, SimpleGrid, Stack, Text } from '@mantine/core';
import {
  IconCpu,
  IconDatabase,
  IconNetwork,
  IconServer,
} from '@tabler/icons-react';
import bytes from 'bytes';
import { FC, ReactNode, useMemo } from 'react';

import { Metric } from './Metric';
import { MiniChart } from './MiniChart';
import { SectionLabel } from './SectionLabel';
import { ACCENT, CYAN } from './colors';
import { formatRate } from './format';
import {
  CurrentMetrics,
  ResourcePoint,
  dualRateData,
  gaugePoints,
} from './history';
import { InstanceInfo } from '@/api/routes/instance/schemas';
import {
  CPU_THRESHOLDS,
  MEMORY_THRESHOLDS,
  levelColor,
} from '@/utils/levelColor';

const HEAD_ICON = {
  size: 15,
  color: 'var(--mantine-color-dimmed)',
  stroke: 1.5,
};
const TILE_H = 240;
/**
 * Uniform tile: header, one primary metric line, one grey caption line,
 * then a chart that fills the remaining height at full width. All text is
 * left-aligned - nothing is stretched to the edges.
 */
const Tile: FC<{
  label: string;
  scope: string;
  icon: ReactNode;
  primary: ReactNode;
  caption: ReactNode;
  chart: ReactNode;
}> = ({ label, scope, icon, primary, caption, chart }) => (
  <Paper withBorder p="md" style={{ height: TILE_H }}>
    <Stack gap="xs" style={{ height: '100%' }}>
      <Group justify="space-between" wrap="nowrap">
        <Group gap={7} wrap="nowrap">
          {icon}
          <Text size="xs" tt="uppercase" lts="1.5px" fw={600} c="dimmed">
            {label}
          </Text>
        </Group>
        <Text size="xs" c="dimmed">
          {scope}
        </Text>
      </Group>
      <Group justify="space-between" wrap="wrap" gap="sm" align="center">
        <Text size="xs" c="dimmed" style={{ whiteSpace: 'nowrap' }}>
          {caption}
        </Text>
        {primary}
      </Group>
      <Box style={{ flex: 1, minHeight: 0 }}>{chart}</Box>
    </Stack>
  </Paper>
);

const pct = (v: number) => `${Math.round(v)}%`;
const rateAxis = (v: number) =>
  bytes(Math.round(v), { decimalPlaces: 1 }) ?? '0';

interface ResourceTilesProps {
  info: InstanceInfo;
  resources: ResourcePoint[];
  current: CurrentMetrics;
}

export const ResourceTiles: FC<ResourceTilesProps> = ({
  info,
  resources,
  current,
}) => {
  const memPct =
    info.memory_total_bytes > 0
      ? (info.memory_used_bytes / info.memory_total_bytes) * 100
      : 0;
  const cpuColor = levelColor(
    info.cpu_percent,
    CPU_THRESHOLDS.warn,
    CPU_THRESHOLDS.bad
  );
  const memColor = levelColor(
    memPct,
    MEMORY_THRESHOLDS.warn,
    MEMORY_THRESHOLDS.bad
  );

  const cpuData = useMemo(() => gaugePoints(resources, 'cpu'), [resources]);
  const memData = useMemo(() => gaugePoints(resources, 'memPct'), [resources]);
  const diskData = useMemo(
    () => dualRateData(resources, 'diskRead', 'diskWrite'),
    [resources]
  );
  const netData = useMemo(
    () => dualRateData(resources, 'netRecv', 'netSent'),
    [resources]
  );

  return (
    <Stack gap="xs">
      <SectionLabel>Resources</SectionLabel>
      <SimpleGrid cols={{ base: 1, xs: 2, lg: 4 }} spacing="md">
        <Tile
          label="CPU"
          scope="host"
          icon={<IconCpu {...HEAD_ICON} />}
          primary={
            <Metric
              value={`${Math.round(info.cpu_percent)}%`}
              color={cpuColor}
            />
          }
          caption={
            <>
              {info.cpu_count ?? '?'} cores ·{' '}
              {Math.round(info.cpu_frequency_mhz)} MHz
            </>
          }
          chart={
            <MiniChart
              data={cpuData}
              series={[{ key: 'value', name: 'CPU', color: cpuColor }]}
              domain={[0, 100]}
              ticks={[0, 25, 50, 75, 100]}
              valueFormatter={pct}
            />
          }
        />

        <Tile
          label="Memory"
          scope="host"
          icon={<IconDatabase {...HEAD_ICON} />}
          primary={<Metric value={`${Math.round(memPct)}%`} color={memColor} />}
          caption={
            <>
              {bytes(info.memory_used_bytes)} · {bytes(info.memory_total_bytes)}{' '}
              total
            </>
          }
          chart={
            <MiniChart
              data={memData}
              series={[{ key: 'value', name: 'Memory', color: memColor }]}
              domain={[0, 100]}
              ticks={[0, 25, 50, 75, 100]}
              valueFormatter={pct}
            />
          }
        />

        <Tile
          label="Disk I/O"
          scope="app"
          icon={<IconServer {...HEAD_ICON} />}
          primary={
            <Group gap="lg" wrap="nowrap">
              <Metric
                value={formatRate(current.diskReadBps)}
                label="read"
                dir="in"
              />
              <Metric
                value={formatRate(current.diskWriteBps)}
                label="write"
                dir="out"
              />
            </Group>
          }
          caption={
            <>
              total {bytes(info.disk_read_bytes)} read ·{' '}
              {bytes(info.disk_written_bytes)} written
            </>
          }
          chart={
            <MiniChart
              data={diskData}
              series={[
                { key: 'in', name: 'Read', color: CYAN },
                { key: 'out', name: 'Write', color: ACCENT },
              ]}
              valueFormatter={formatRate}
              tickFormatter={rateAxis}
            />
          }
        />

        <Tile
          label="Network"
          scope="app"
          icon={<IconNetwork {...HEAD_ICON} />}
          primary={
            <Group gap="lg" wrap="nowrap">
              <Metric
                value={formatRate(current.netRecvBps)}
                label="in"
                dir="in"
              />
              <Metric
                value={formatRate(current.netSentBps)}
                label="out"
                dir="out"
              />
            </Group>
          }
          caption={
            <>
              total {bytes(info.network_received_bytes)} in ·{' '}
              {bytes(info.network_sent_bytes)} out
            </>
          }
          chart={
            <MiniChart
              data={netData}
              series={[
                { key: 'in', name: 'In', color: CYAN },
                { key: 'out', name: 'Out', color: ACCENT },
              ]}
              valueFormatter={formatRate}
              tickFormatter={rateAxis}
            />
          }
        />
      </SimpleGrid>
    </Stack>
  );
};
