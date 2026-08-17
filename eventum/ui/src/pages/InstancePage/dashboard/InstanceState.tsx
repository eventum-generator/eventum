import { Group, Text } from '@mantine/core';
import {
  IconAlertTriangle,
  IconArrowsSplit2,
  IconClockPlay,
  IconTrash,
} from '@tabler/icons-react';
import { FC } from 'react';

import { formatCompact, formatEps } from '../format';
import { GeneratorStats } from '@/api/routes/generators/schemas';
import { Reading } from '@/components/ui/Reading';

const DANGER = 'var(--mantine-color-red-text)';

/** One cumulative total of the run. */
const Total: FC<{ value: number; label: string }> = ({ value, label }) => (
  <Text size="xs" c="dimmed" style={{ whiteSpace: 'nowrap' }}>
    {formatCompact(value)} {label}
  </Text>
);

interface InstanceStateProps {
  stats: GeneratorStats;
  inputEps: number;
  outputEps: number;
}

/**
 * What the instance is moving right now and what it has moved since it
 * started. The figures below it in the same panel say what that costs, so
 * nothing here repeats them.
 */
export const InstanceState: FC<InstanceStateProps> = ({
  stats,
  inputEps,
  outputEps,
}) => {
  const failed =
    stats.event.produce_failed +
    stats.output.reduce(
      (sum, plugin) => sum + plugin.write_failed + plugin.format_failed,
      0
    );

  return (
    <Group justify="space-between" gap="md" wrap="wrap">
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

      <Group gap="xs" wrap="wrap" align="center">
        <Total value={stats.total_generated} label="generated" />
        <Text size="xs" c="dimmed">
          ·
        </Text>
        <Total value={stats.event.produced} label="produced" />
        <Text size="xs" c="dimmed">
          ·
        </Text>
        <Total value={stats.total_written} label="written" />
      </Group>
    </Group>
  );
};
