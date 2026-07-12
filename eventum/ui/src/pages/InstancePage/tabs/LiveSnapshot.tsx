import { Group, SimpleGrid, Skeleton, Text } from '@mantine/core';
import { IconClock } from '@tabler/icons-react';
import { FC, useEffect } from 'react';

import { formatCompact, formatEps, formatUptime } from '../format';
import { StatTile } from '../primitives';
import { useGeneratorStats } from '@/api/hooks/useGenerators';

interface LiveSnapshotProps {
  instanceId: string;
}

/**
 * At-a-glance live counters for a running instance. Mounted only while the
 * instance runs, so its polling stops when the instance is stopped or the
 * user leaves the tab.
 */
export const LiveSnapshot: FC<LiveSnapshotProps> = ({ instanceId }) => {
  const { data: stats, isLoading, refetch } = useGeneratorStats(instanceId);

  useEffect(() => {
    const interval = setInterval(() => void refetch(), 3000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (isLoading || !stats) {
    return <Skeleton h={92} radius="md" />;
  }

  return (
    <div>
      <Group gap={7} wrap="nowrap" align="center" mb="xs">
        <IconClock size={14} color="var(--ev-muted)" />
        <Text size="xs" c="dimmed">
          Uptime {formatUptime(stats.uptime)}
        </Text>
      </Group>
      <SimpleGrid cols={{ base: 2, sm: 4 }} spacing="sm">
        <StatTile
          label="Generated"
          value={formatCompact(stats.total_generated)}
        />
        <StatTile label="Written" value={formatCompact(stats.total_written)} />
        <StatTile
          label="Input"
          value={formatEps(stats.input_eps)}
          unit="eps"
          color="var(--ev-cyan)"
        />
        <StatTile
          label="Output"
          value={formatEps(stats.output_eps)}
          unit="eps"
          color="var(--ev-accent)"
        />
      </SimpleGrid>
    </div>
  );
};
