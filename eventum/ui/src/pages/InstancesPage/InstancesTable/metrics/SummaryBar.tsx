import { Grid, Paper, Text } from '@mantine/core';
import { FC } from 'react';

import type { GeneratorStats } from '@/api/routes/generators/schemas';

function formatUptime(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.round(seconds % 60);
  if (h > 0) return `${h}h ${m}m ${s}s`;
  if (m > 0) return `${m}m ${String(s).padStart(2, '0')}s`;
  return `${s}s`;
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <Text size="xs" c="dimmed">
        {label}
      </Text>
      <Text size="sm" fw={500}>
        {value}
      </Text>
    </div>
  );
}

interface SummaryBarProps {
  stats: GeneratorStats;
}

export const SummaryBar: FC<SummaryBarProps> = ({ stats }) => {
  return (
    <Paper withBorder p="md">
      <Grid>
        <Grid.Col span={3}>
          <Stat label="Instance" value={stats.id} />
        </Grid.Col>
        <Grid.Col span={3}>
          <Stat label="Start time" value={new Date(stats.start_time).toLocaleString()} />
        </Grid.Col>
        <Grid.Col span={3}>
          <Stat label="Uptime" value={formatUptime(stats.uptime)} />
        </Grid.Col>
        <Grid.Col span={3}>
          <Stat label="Generated" value={stats.total_generated} />
        </Grid.Col>
        <Grid.Col span={3}>
          <Stat label="Written" value={stats.total_written} />
        </Grid.Col>
        <Grid.Col span={3}>
          <Stat label="Input EPS" value={stats.input_eps.toFixed(2)} />
        </Grid.Col>
        <Grid.Col span={3}>
          <Stat label="Output EPS" value={stats.output_eps.toFixed(2)} />
        </Grid.Col>
      </Grid>
    </Paper>
  );
};
