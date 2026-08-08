import {
  Group,
  Progress,
  SimpleGrid,
  Stack,
  Text,
  Tooltip,
} from '@mantine/core';
import { FC } from 'react';

import { formatUptime } from '../format';
import { Section } from '../primitives';
import { ResourcesStats } from '@/api/routes/generators/schemas';
import { CPU_THRESHOLDS, levelColor } from '@/utils/levelColor';

/** A queue fill level as a labelled bar. */
const QueueFill: FC<{ label: string; size: number; maxsize: number }> = ({
  label,
  size,
  maxsize,
}) => {
  const percent = (size / maxsize) * 100;

  return (
    <Stack gap={4}>
      <Group justify="space-between" gap="xs">
        <Text size="xs" c="dimmed">
          {label}
        </Text>
        <Text size="xs" ff="monospace">
          {size} / {maxsize}
        </Text>
      </Group>
      <Progress
        value={percent}
        color={percent >= 100 ? 'yellow' : 'primary'}
        size="sm"
        aria-label={`${label} queue fill`}
      />
    </Stack>
  );
};

/** One figure with its caption underneath. */
const Figure: FC<{ label: string; value: string; color?: string }> = ({
  label,
  value,
  color,
}) => (
  <Stack gap={2}>
    <Text size="xl" fw={600} c={color}>
      {value}
    </Text>
    <Text size="xs" c="dimmed">
      {label}
    </Text>
  </Stack>
);

interface ResourcesPanelProps {
  resources: ResourcesStats;
  cpuPercent: number;
}

/**
 * What the instance costs the host it shares with the others: its share of a
 * CPU core over the last poll interval, the CPU time it has spent in total,
 * the threads it runs, and how full the queues between its stages are. A
 * queue that stays full is the instance waiting on its own next stage, so it
 * reads as the pressure inside the pipeline rather than a fault.
 *
 * Memory is deliberately absent - instances share one process heap, so no
 * per-instance figure for it exists to report.
 */
export const ResourcesPanel: FC<ResourcesPanelProps> = ({
  resources,
  cpuPercent,
}) => (
  <Section label="Resources">
    <SimpleGrid cols={{ base: 2, sm: 4 }} spacing="md">
      <Tooltip label="Share of one CPU core over the last poll interval">
        <Figure
          label="CPU"
          value={`${cpuPercent.toFixed(1)}%`}
          color={levelColor(
            cpuPercent,
            CPU_THRESHOLDS.warn,
            CPU_THRESHOLDS.bad
          )}
        />
      </Tooltip>
      <Figure label="CPU time" value={formatUptime(resources.cpu_seconds)} />
      <Figure label="Threads" value={String(resources.thread_count)} />
      <Stack gap="xs">
        <QueueFill
          label="Timestamps"
          size={resources.queues.timestamps.size}
          maxsize={resources.queues.timestamps.maxsize}
        />
        <QueueFill
          label="Events"
          size={resources.queues.events.size}
          maxsize={resources.queues.events.maxsize}
        />
      </Stack>
    </SimpleGrid>
  </Section>
);
