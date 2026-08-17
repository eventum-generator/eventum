import { Skeleton, Stack } from '@mantine/core';
import { ReactFlowProvider } from '@xyflow/react';
import { FC } from 'react';

import { Section } from '../primitives';
import { InstanceState } from './InstanceState';
import { ResourcesPanel } from './ResourcesPanel';
import { GeneratorStats } from '@/api/routes/generators/schemas';
import { PipelineFlow } from '@/pages/InstancesPage/InstancesTable/metrics/PipelineGraph';
import { ThroughputChart } from '@/pages/MonitoringPage/ThroughputChart';
import type { FlowPoint } from '@/pages/MonitoringPage/history';

interface InstanceDashboardProps {
  stats: GeneratorStats | undefined;
  flow: FlowPoint[];
  inputEps: number;
  outputEps: number;
  cpuPercent: number;
}

/**
 * Live behaviour of a running instance, ordered from what it is doing now to
 * the detail behind it: the state of the pipeline in one line, its throughput
 * over the window, the stage-by-stage graph, then what it occupies. A pure
 * renderer - polling and point history live in the page shell
 * (`useInstanceHistory`), so the throughput history survives tab switches
 * instead of rebuilding from zero.
 */
export const InstanceDashboard: FC<InstanceDashboardProps> = ({
  stats,
  flow,
  inputEps,
  outputEps,
  cpuPercent,
}) => {
  if (!stats) {
    return <Skeleton h={340} radius="lg" />;
  }

  return (
    <Stack gap="lg">
      <InstanceState
        stats={stats}
        inputEps={inputEps}
        outputEps={outputEps}
        cpuPercent={cpuPercent}
      />
      <ThroughputChart flow={flow} inputEps={inputEps} outputEps={outputEps} />
      <Section label="Pipeline">
        <ReactFlowProvider>
          <PipelineFlow stats={stats} />
        </ReactFlowProvider>
      </Section>
      <ResourcesPanel resources={stats.resources} cpuPercent={cpuPercent} />
    </Stack>
  );
};
