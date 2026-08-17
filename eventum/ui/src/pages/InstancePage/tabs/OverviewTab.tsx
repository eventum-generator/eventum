import { Divider, Grid, Skeleton, Stack, Text } from '@mantine/core';
import { ReactFlowProvider } from '@xyflow/react';
import { FC } from 'react';

import { AboutPanel } from '../dashboard/AboutPanel';
import { LivePanel } from '../dashboard/LivePanel';
import { Section, SectionLabel } from '../primitives';
import { ScenariosCard } from './ScenariosCard';
import {
  GeneratorParameters,
  GeneratorStats,
  GeneratorStatus,
} from '@/api/routes/generators/schemas';
import { PipelineFlow } from '@/pages/InstancesPage/InstancesTable/metrics/PipelineGraph';
import { ThroughputChart } from '@/pages/MonitoringPage/ThroughputChart';
import type { FlowPoint } from '@/pages/MonitoringPage/history';

interface OverviewTabProps {
  instanceId: string;
  status: GeneratorStatus;
  generatorParams: GeneratorParameters;
  liveMode: boolean;
  autostart: boolean;
  memberScenarios: string[];
  allScenarios: string[];
  stats: GeneratorStats | undefined;
  flow: FlowPoint[];
  inputEps: number;
  outputEps: number;
  cpuPercent: number;
}

/**
 * The instance from its state down to the views that explain it: what it is
 * doing right now and what that costs across the full width, then its
 * throughput over the window next to what the instance is, then the
 * stage-by-stage graph across the full width again.
 */
export const OverviewTab: FC<OverviewTabProps> = ({
  instanceId,
  status,
  generatorParams,
  liveMode,
  autostart,
  memberScenarios,
  allScenarios,
  stats,
  flow,
  inputEps,
  outputEps,
  cpuPercent,
}) => (
  <Stack gap="lg">
    {status.is_running && stats && (
      <LivePanel
        stats={stats}
        inputEps={inputEps}
        outputEps={outputEps}
        cpuPercent={cpuPercent}
      />
    )}

    <Grid gutter="lg">
      <Grid.Col span={{ base: 12, md: 8 }}>
        {!status.is_running ? (
          <Section label="Now">
            <Text size="sm" c="dimmed">
              Instance is not running. Start it to see what it produces and what
              it occupies.
            </Text>
          </Section>
        ) : stats ? (
          <ThroughputChart
            flow={flow}
            inputEps={inputEps}
            outputEps={outputEps}
            height={200}
          />
        ) : (
          <Skeleton h={260} radius="lg" />
        )}
      </Grid.Col>
      <Grid.Col span={{ base: 12, md: 4 }}>
        <Section label="About">
          <Stack gap="md">
            <AboutPanel
              instanceId={instanceId}
              generatorParams={generatorParams}
              liveMode={liveMode}
              autostart={autostart}
            />
            <Divider />
            <Stack gap="sm">
              <SectionLabel>Scenarios</SectionLabel>
              <ScenariosCard
                instanceId={instanceId}
                memberScenarios={memberScenarios}
                allScenarios={allScenarios}
              />
            </Stack>
          </Stack>
        </Section>
      </Grid.Col>
    </Grid>

    {status.is_running && stats && (
      <Section label="Pipeline">
        <ReactFlowProvider>
          <PipelineFlow stats={stats} />
        </ReactFlowProvider>
      </Section>
    )}
  </Stack>
);
