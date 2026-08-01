import { Grid, Stack, Text } from '@mantine/core';
import { FC } from 'react';

import { AboutPanel } from '../dashboard/AboutPanel';
import { InstanceDashboard } from '../dashboard/InstanceDashboard';
import { Section } from '../primitives';
import { ScenariosCard } from './ScenariosCard';
import {
  GeneratorParameters,
  GeneratorStats,
  GeneratorStatus,
} from '@/api/routes/generators/schemas';
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
}

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
}) => (
  <Grid gutter="lg">
    <Grid.Col span={{ base: 12, md: 8 }}>
      {status.is_running ? (
        <InstanceDashboard
          stats={stats}
          flow={flow}
          inputEps={inputEps}
          outputEps={outputEps}
        />
      ) : (
        <Section label="Pipeline">
          <Text size="sm" c="dimmed">
            Instance is not running. Start it to see live pipeline activity.
          </Text>
        </Section>
      )}
    </Grid.Col>
    <Grid.Col span={{ base: 12, md: 4 }}>
      <Stack gap="lg">
        <Section label="About">
          <AboutPanel
            instanceId={instanceId}
            generatorParams={generatorParams}
            liveMode={liveMode}
            autostart={autostart}
          />
        </Section>
        <Section label="Scenarios">
          <ScenariosCard
            instanceId={instanceId}
            memberScenarios={memberScenarios}
            allScenarios={allScenarios}
          />
        </Section>
      </Stack>
    </Grid.Col>
  </Grid>
);
