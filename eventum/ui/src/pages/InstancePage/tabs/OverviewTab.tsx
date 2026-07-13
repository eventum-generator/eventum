import { Grid, Stack, Text } from '@mantine/core';
import { FC } from 'react';

import { AboutPanel } from '../dashboard/AboutPanel';
import { InstanceDashboard } from '../dashboard/InstanceDashboard';
import { Section } from '../primitives';
import { ScenariosCard } from './ScenariosCard';
import {
  GeneratorParameters,
  GeneratorStatus,
} from '@/api/routes/generators/schemas';

interface OverviewTabProps {
  instanceId: string;
  status: GeneratorStatus;
  generatorParams: GeneratorParameters;
  liveMode: boolean;
  memberScenarios: string[];
  allScenarios: string[];
}

export const OverviewTab: FC<OverviewTabProps> = ({
  instanceId,
  status,
  generatorParams,
  liveMode,
  memberScenarios,
  allScenarios,
}) => (
  <Grid gutter="lg">
    <Grid.Col span={{ base: 12, md: 8 }}>
      <Section label="Pipeline">
        {status.is_running ? (
          <InstanceDashboard instanceId={instanceId} />
        ) : (
          <Text size="sm" c="dimmed">
            Instance is not running. Start it to see live pipeline activity.
          </Text>
        )}
      </Section>
    </Grid.Col>
    <Grid.Col span={{ base: 12, md: 4 }}>
      <Stack gap="xl">
        <Section label="About">
          <AboutPanel
            instanceId={instanceId}
            generatorParams={generatorParams}
            liveMode={liveMode}
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
