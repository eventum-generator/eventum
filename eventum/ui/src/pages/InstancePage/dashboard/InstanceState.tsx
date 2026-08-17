import { Divider, Group, Paper } from '@mantine/core';
import {
  IconAlertTriangle,
  IconArrowsSplit2,
  IconClockPlay,
  IconCpu,
  IconStack2,
  IconTrash,
} from '@tabler/icons-react';
import { FC } from 'react';

import { formatCompact, formatEps } from '../format';
import { GeneratorStats } from '@/api/routes/generators/schemas';
import { Reading } from '@/components/ui/Reading';
import {
  CPU_THRESHOLDS,
  QUEUE_THRESHOLDS,
  levelColor,
} from '@/utils/levelColor';

const DANGER = 'var(--mantine-color-red-text)';

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
 * its limit the fullest of its queues is, and what it has lost. An icon
 * separates the figures; a colour appears only where one needs attention.
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
      <Group gap="lg" wrap="wrap" align="center">
        <Reading
          icon={IconClockPlay}
          value={`${formatEps(inputEps)}/s`}
          label="input"
        />
        <Reading
          icon={IconArrowsSplit2}
          value={`${formatEps(outputEps)}/s`}
          label="output"
        />
        <Divider orientation="vertical" />
        <Reading
          icon={IconCpu}
          value={`${cpuPercent.toFixed(1)}%`}
          label="of a core"
          color={
            cpuPercent >= CPU_THRESHOLDS.warn
              ? levelColor(cpuPercent, CPU_THRESHOLDS.warn, CPU_THRESHOLDS.bad)
              : undefined
          }
        />
        <Reading
          icon={IconStack2}
          value={`${Math.round(queuePeak)}%`}
          label="fullest queue"
          color={
            queuePeak >= QUEUE_THRESHOLDS.warn
              ? levelColor(
                  queuePeak,
                  QUEUE_THRESHOLDS.warn,
                  QUEUE_THRESHOLDS.bad
                )
              : undefined
          }
        />
        <Divider orientation="vertical" />
        <Reading
          icon={IconAlertTriangle}
          value={formatCompact(failed)}
          label="failed"
          color={failed > 0 ? DANGER : undefined}
        />
        <Reading
          icon={IconTrash}
          value={formatCompact(stats.event.dropped)}
          label="dropped"
        />
      </Group>
    </Paper>
  );
};
