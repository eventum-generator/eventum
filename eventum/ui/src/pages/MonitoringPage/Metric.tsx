import { Group, Text } from '@mantine/core';
import { IconArrowDown, IconArrowUp } from '@tabler/icons-react';
import { FC } from 'react';

import { ACCENT, CYAN } from './colors';

const VALUE_SIZE = '1.25rem';

interface MetricProps {
  value: string;
  label?: string;
  color?: string;
  dir?: 'in' | 'out';
}

/**
 * Shared live-metric readout: a bold coloured value with an optional unit.
 * Used by the resource tiles and the chart headers so every current-value
 * stat on the Monitoring page reads in one consistent style. Flow metrics
 * pass `dir` to prepend a direction arrow and take the matching channel
 * colour; other metrics pass an explicit `color`.
 */
export const Metric: FC<MetricProps> = ({ value, label, color, dir }) => (
  <Group gap={6} wrap="nowrap" align="center">
    {dir === 'in' && <IconArrowDown size={15} color={CYAN} />}
    {dir === 'out' && <IconArrowUp size={15} color={ACCENT} />}
    <Text
      fw={700}
      ff="monospace"
      style={{
        fontSize: VALUE_SIZE,
        color: dir ? (dir === 'in' ? CYAN : ACCENT) : color,
        fontVariantNumeric: 'tabular-nums',
        lineHeight: 1,
      }}
    >
      {value}
    </Text>
    {label ? (
      <Text size="sm" c="dimmed">
        {label}
      </Text>
    ) : null}
  </Group>
);
