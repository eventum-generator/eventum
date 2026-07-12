import { Grid, Paper, Stack, Text } from '@mantine/core';
import { FC } from 'react';

import { Section, SectionLabel } from '../primitives';
import { LiveSnapshot } from './LiveSnapshot';
import { ScenariosCard } from './ScenariosCard';
import { WiringCard } from './WiringCard';
import {
  GeneratorParameters,
  GeneratorStatus,
} from '@/api/routes/generators/schemas';

interface OverviewTabProps {
  instanceId: string;
  status: GeneratorStatus;
  generatorParams: GeneratorParameters;
  liveMode: boolean;
  autostart: boolean;
  memberScenarios: string[];
  allScenarios: string[];
}

export const OverviewTab: FC<OverviewTabProps> = ({
  instanceId,
  status,
  generatorParams,
  liveMode,
  autostart,
  memberScenarios,
  allScenarios,
}) => {
  const isRunning = status.is_running;

  return (
    <Stack gap="xl">
      <Stack gap="xs">
        <SectionLabel>Live throughput</SectionLabel>
        {isRunning ? (
          <LiveSnapshot instanceId={instanceId} />
        ) : (
          <Paper withBorder radius="md" p="lg">
            <Text size="sm" c="dimmed">
              Instance is not running. Live throughput appears here while it
              runs.
            </Text>
          </Paper>
        )}
      </Stack>

      <Grid gutter="lg">
        <Grid.Col span={{ base: 12, md: 7 }}>
          <Section label="Configuration">
            <WiringCard
              generatorParams={generatorParams}
              liveMode={liveMode}
              autostart={autostart}
            />
          </Section>
        </Grid.Col>
        <Grid.Col span={{ base: 12, md: 5 }}>
          <Section label="Scenarios">
            <ScenariosCard
              instanceId={instanceId}
              memberScenarios={memberScenarios}
              allScenarios={allScenarios}
            />
          </Section>
        </Grid.Col>
      </Grid>
    </Stack>
  );
};
