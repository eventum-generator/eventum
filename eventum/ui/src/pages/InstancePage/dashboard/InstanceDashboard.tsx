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
 * Live behaviour of a running instance: the throughput graph over the live
 * pipeline graph. A pure renderer - polling and point history live in the
 * page shell (`useInstanceHistory`), so the throughput history survives tab
 * switches instead of rebuilding from zero.
 */
export const InstanceDashboard: FC<InstanceDashboardProps> = ({
  stats,
  flow,
  inputEps,
  outputEps,
}) => {
  if (!stats) {
    return <Skeleton h={340} radius="md" />;
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
