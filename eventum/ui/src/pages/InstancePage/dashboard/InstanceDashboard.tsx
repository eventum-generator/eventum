import { SimpleGrid, Skeleton, Stack } from '@mantine/core';
import { ReactFlowProvider } from '@xyflow/react';
import { FC } from 'react';

import { formatCompact, formatEps } from '../format';
import { StatTile } from '../primitives';
import { useInstanceHistory } from './useInstanceHistory';
import { GeneratorStats } from '@/api/routes/generators/schemas';
import { PipelineGraph } from '@/pages/InstancesPage/InstancesTable/metrics/PipelineGraph';
import { ErrorsChart } from '@/pages/MonitoringPage/ErrorsChart';
import { ThroughputChart } from '@/pages/MonitoringPage/ThroughputChart';

function countErrors(stats: GeneratorStats): number {
  const outputFailed = stats.output.reduce(
    (sum, p) => sum + p.write_failed + p.format_failed,
    0
  );
  return stats.event.produce_failed + outputFailed;
}

/**
 * Live behaviour of a running instance: current counters, rolling throughput
 * and failure charts, and the live per-plugin pipeline. Mounted only while
 * the instance runs, so its polling stops when it is stopped.
 */
export const InstanceDashboard: FC<{ instanceId: string }> = ({
  instanceId,
}) => {
  const { stats, flow, inputEps, outputEps, failing } =
    useInstanceHistory(instanceId);

  if (!stats) {
    return <Skeleton h={420} radius="md" />;
  }

  const errors = countErrors(stats);

  return (
    <Stack gap="lg">
      <SimpleGrid cols={{ base: 2, sm: 3 }} spacing="sm">
        <StatTile
          label="Generated"
          value={formatCompact(stats.total_generated)}
        />
        <StatTile label="Written" value={formatCompact(stats.total_written)} />
        <StatTile
          label="Input"
          value={formatEps(inputEps)}
          unit="eps"
          color="var(--ev-cyan)"
        />
        <StatTile
          label="Output"
          value={formatEps(outputEps)}
          unit="eps"
          color="var(--ev-accent)"
        />
        <StatTile
          label="Errors"
          value={formatCompact(errors)}
          color={errors > 0 ? 'var(--ev-bad)' : undefined}
        />
        <StatTile label="Dropped" value={formatCompact(stats.event.dropped)} />
      </SimpleGrid>

      <ThroughputChart flow={flow} inputEps={inputEps} outputEps={outputEps} />

      {failing && <ErrorsChart flow={flow} />}

      <ReactFlowProvider>
        <PipelineGraph stats={stats} />
      </ReactFlowProvider>
    </Stack>
  );
};
