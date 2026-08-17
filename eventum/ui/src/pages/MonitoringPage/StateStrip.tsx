import { Divider, Group, Paper, Text } from '@mantine/core';
import { FC } from 'react';

import { ACCENT, CYAN } from './colors';
import { formatCompact, formatEps } from './format';
import { CurrentMetrics, InstanceUsageRow } from './history';
import { FlowAgg } from './metrics';
import { useAnimatedNumber } from './useAnimatedNumber';
import { GeneratorStatus } from '@/api/routes/generators/schemas';
import { StatusDot } from '@/components/ui/StatusDot';
import { QUEUE_THRESHOLDS, levelColor } from '@/utils/levelColor';

const RUNNING: GeneratorStatus = {
  is_running: true,
  is_initializing: false,
  is_stopping: false,
  is_ended_up: false,
  is_ended_up_successfully: false,
};

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

/** One cumulative total, counting up to its new value on each poll. */
const Total: FC<{ value: number; label: string }> = ({ value, label }) => {
  const shown = useAnimatedNumber(value);
  return (
    <Text size="xs" c="dimmed" style={{ whiteSpace: 'nowrap' }}>
      {formatCompact(Math.round(shown))} {label}
    </Text>
  );
};

interface StateStripProps {
  flow: FlowAgg;
  current: CurrentMetrics;
  rows: InstanceUsageRow[];
  instances: number;
}

/**
 * The state of the whole pipeline in one line: how many instances run, the
 * rate each stage moves events at, whether anything fails, and how close to
 * its limit the fullest events queue is. Everything below the strip explains
 * one of these figures.
 */
export const StateStrip: FC<StateStripProps> = ({
  flow,
  current,
  rows,
  instances,
}) => {
  let queuePeak = 0;
  for (const row of rows) queuePeak = Math.max(queuePeak, row.queuePercent);

  return (
    <Paper withBorder px="md" py="sm">
      <Group justify="space-between" gap="md" wrap="wrap">
        <Group gap="md" wrap="wrap" align="center">
          <Group gap={8} wrap="nowrap" align="center">
            <StatusDot status={RUNNING} />
            <Reading
              value={String(instances)}
              label={instances === 1 ? 'instance' : 'instances'}
            />
          </Group>
          <Divider orientation="vertical" />
          <Reading
            value={`${formatEps(current.inputEps)}/s`}
            label="input"
            color={CYAN}
          />
          <Reading
            value={`${formatEps(current.producedEps)}/s`}
            label="event"
          />
          <Reading
            value={`${formatEps(current.outputEps)}/s`}
            label="output"
            color={ACCENT}
          />
          <Divider orientation="vertical" />
          <Reading
            value={`${formatEps(current.failEps)}/s`}
            label="failing"
            color={
              current.failEps > 0 ? 'var(--mantine-color-red-text)' : undefined
            }
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
        </Group>

        <Group gap="xs" wrap="wrap" align="center">
          <Total value={flow.generated} label="generated" />
          <Text size="xs" c="dimmed">
            ·
          </Text>
          <Total value={flow.produced} label="produced" />
          <Text size="xs" c="dimmed">
            ·
          </Text>
          <Total value={flow.written} label="written" />
          <Text size="xs" c="dimmed">
            ·
          </Text>
          <Total value={flow.dropped} label="dropped" />
        </Group>
      </Group>
    </Paper>
  );
};
