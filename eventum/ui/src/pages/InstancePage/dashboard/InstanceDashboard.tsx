import { Skeleton, Stack } from '@mantine/core';
import { ReactFlowProvider } from '@xyflow/react';
import { FC } from 'react';

import { Section } from '../primitives';
import { GeneratorStats } from '@/api/routes/generators/schemas';
import { PipelineFlow } from '@/pages/InstancesPage/InstancesTable/metrics/PipelineGraph';
import { ThroughputChart } from '@/pages/MonitoringPage/ThroughputChart';
import type { FlowPoint } from '@/pages/MonitoringPage/history';

interface InstanceDashboardProps {
  stats: GeneratorStats | undefined;
  flow: FlowPoint[];
  inputEps: number;
  outputEps: number;
}

/**
 * What a running instance is doing: its throughput over the window, then the
 * stage-by-stage graph behind that figure. A pure renderer - polling and point
 * history live in the page shell (`useInstanceHistory`), so the throughput
 * history survives tab switches instead of rebuilding from zero.
 */
export const InstanceDashboard: FC<InstanceDashboardProps> = ({
  stats,
  flow,
  inputEps,
  outputEps,
}) => {
  if (!stats) {
    return <Skeleton h={340} radius="lg" />;
  }

  return (
    <Stack gap="lg">
      <ThroughputChart flow={flow} inputEps={inputEps} outputEps={outputEps} />
      <Section label="Pipeline">
        <ReactFlowProvider>
          <PipelineFlow stats={stats} />
        </ReactFlowProvider>
      </Section>
    </Stack>
  );
};
