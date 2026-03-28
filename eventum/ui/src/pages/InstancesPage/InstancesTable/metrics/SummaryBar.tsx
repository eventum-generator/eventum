import { Group, Paper, SimpleGrid, Text } from '@mantine/core';
import { IconClock, IconPointFilled } from '@tabler/icons-react';
import { intervalToDuration } from 'date-fns';
import { FC } from 'react';

import type { GeneratorStats } from '@/api/routes/generators/schemas';

function formatUptime(seconds: number): string {
  const { days = 0, hours = 0, minutes = 0, seconds: secs = 0 } = intervalToDuration({
    start: 0,
    end: seconds * 1000,
  });
  if (days > 0) return `${days}d ${hours}h ${minutes}m`;
  if (hours > 0) return `${hours}h ${minutes}m ${secs}s`;
  if (minutes > 0) return `${minutes}m ${String(secs).padStart(2, '0')}s`;
  return `${secs}s`;
}

function StatCard({ value, label }: { value: string | number; label: string }) {
  return (
    <Paper withBorder p="xs" radius="md">
      <Text size="md" fw={600} lh={1.2}>
        {value}
      </Text>
      <Text size="xs" c="dimmed" mt={2}>
        {label}
      </Text>
    </Paper>
  );
}

interface SummaryBarProps {
  stats: GeneratorStats;
}

export const SummaryBar: FC<SummaryBarProps> = ({ stats }) => {
  return (
    <div>
      <Group justify="space-between" mb="sm">
        <div>
          <Text size="md" fw={600}>{stats.id}</Text>
          <Group gap="xs" mt={2}>
            <IconClock size={14} color="var(--mantine-color-dimmed)" />
            <Text size="xs" c="dimmed">
              Started {new Date(stats.start_time).toLocaleString()}
            </Text>
            <IconPointFilled size={8} color="var(--mantine-color-dimmed)" />
            <Text size="xs" c="dimmed">
              Uptime {formatUptime(stats.uptime)}
            </Text>
          </Group>
        </div>
      </Group>

      <SimpleGrid cols={4} spacing="sm">
        <StatCard value={stats.total_generated} label="Generated" />
        <StatCard value={stats.total_written} label="Written" />
        <StatCard value={stats.input_eps.toFixed(2)} label="Input EPS" />
        <StatCard value={stats.output_eps.toFixed(2)} label="Output EPS" />
      </SimpleGrid>
    </div>
  );
};
