import { Divider, Group, Paper, Text } from '@mantine/core';
import { FC } from 'react';

import { formatCompact, formatEps } from '../format';
import { GeneratorStats } from '@/api/routes/generators/schemas';
import {
  CPU_THRESHOLDS,
  QUEUE_THRESHOLDS,
  levelColor,
} from '@/utils/levelColor';

/** One live reading: the figure and what it is. */
const Reading: FC<{ value: string; label: string; color?: string }> = ({
  value,
  label,
  color,
}) => (
  <Group gap={6} wrap="nowrap" align="baseline">
    <Text
      size="md"
      fw={700}
      ff="monospace"
      c={color}
      style={{ fontVariantNumeric: 'tabular-nums' }}
    >
      {value}
    </Text>
    <Text size="xs" c="dimmed">
      {label}
    </Text>
  </Group>
);

/** Fill level of a queue: the fuller of the batches and the bytes it holds. */
function fill(queue: {
  size: number;
  maxsize: number;
  size_bytes: number;
  max_bytes: number | null;
}): number {
  const batches = queue.maxsize > 0 ? (queue.size / queue.maxsize) * 100 : 0;
  const held = queue.max_bytes ? (queue.size_bytes / queue.max_bytes) * 100 : 0;
  return Math.max(batches, held);
}

interface InstanceStateProps {
  stats: GeneratorStats;
  inputEps: number;
  outputEps: number;
  cpuPercent: number;
}

/**
 * What the instance is doing right now, in one line above the detail: the rate
 * events enter and leave the pipeline at, the processor it takes, how close to
 * its limit the fullest of its queues is, and whether anything has failed.
 */
export const InstanceState: FC<InstanceStateProps> = ({
  stats,
  inputEps,
  outputEps,
  cpuPercent,
}) => {
  const failed =
    stats.event.produce_failed +
    stats.output.reduce(
      (sum, plugin) => sum + plugin.write_failed + plugin.format_failed,
      0
    );
  const queuePeak = Math.max(
    fill(stats.resources.queues.timestamps),
    fill(stats.resources.queues.events)
  );

  return (
    <Paper withBorder px="md" py="sm">
      <Group gap="md" wrap="wrap" align="center">
        <Reading value={`${formatEps(inputEps)}/s`} label="input" />
        <Reading value={`${formatEps(outputEps)}/s`} label="output" />
        <Divider orientation="vertical" />
        <Reading
          value={`${cpuPercent.toFixed(1)}%`}
          label="of a core"
          color={levelColor(
            cpuPercent,
            CPU_THRESHOLDS.warn,
            CPU_THRESHOLDS.bad
          )}
        />
        <Reading
          value={`${Math.round(queuePeak)}%`}
          label="fullest queue"
          color={levelColor(
            queuePeak,
            QUEUE_THRESHOLDS.warn,
            QUEUE_THRESHOLDS.bad
          )}
        />
        <Divider orientation="vertical" />
        <Reading
          value={formatCompact(failed)}
          label="failed"
          color={failed > 0 ? 'var(--mantine-color-red-text)' : undefined}
        />
        <Reading value={formatCompact(stats.event.dropped)} label="dropped" />
      </Group>
    </Paper>
  );
};
