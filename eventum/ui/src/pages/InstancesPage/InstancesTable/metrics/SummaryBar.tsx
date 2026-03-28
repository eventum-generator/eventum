import { Divider, Group, Text } from '@mantine/core';
import { FC, Fragment } from 'react';

import type { GeneratorStats } from '@/api/routes/generators/schemas';

function formatUptime(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.round(seconds % 60);
  if (h > 0) return `${h}h ${m}m ${s}s`;
  if (m > 0) return `${m}m ${String(s).padStart(2, '0')}s`;
  return `${s}s`;
}

interface SummaryBarProps {
  stats: GeneratorStats;
}

export const SummaryBar: FC<SummaryBarProps> = ({ stats }) => {
  const items = [
    { label: 'Instance', value: stats.id },
    { label: 'Start', value: new Date(stats.start_time).toLocaleString() },
    { label: 'Uptime', value: formatUptime(stats.uptime) },
    { label: 'Generated', value: stats.total_generated },
    { label: 'Written', value: stats.total_written },
    { label: 'In EPS', value: stats.input_eps.toFixed(2) },
    { label: 'Out EPS', value: stats.output_eps.toFixed(2) },
  ];

  return (
    <Group gap="sm" wrap="nowrap">
      {items.map((item, i) => (
        <Fragment key={item.label}>
          {i > 0 && <Divider orientation="vertical" />}
          <Group gap={4} wrap="nowrap">
            <Text size="xs" c="dimmed">
              {item.label}:
            </Text>
            <Text size="xs" fw={500}>
              {item.value}
            </Text>
          </Group>
        </Fragment>
      ))}
    </Group>
  );
};
