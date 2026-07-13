import { Center, Grid, Paper, Stack, Text } from '@mantine/core';
import { IconChartLine } from '@tabler/icons-react';
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

const NotRunning: FC = () => (
  <Paper withBorder radius="md" p="xl">
    <Center>
      <Stack align="center" gap="xs" py="xl">
        <IconChartLine size={32} color="var(--ev-faint)" stroke={1.5} />
        <Text size="sm" c="dimmed" ta="center" maw={360}>
          Instance is not running. Start it to see live throughput, failures and
          the pipeline.
        </Text>
      </Stack>
    </Center>
  </Paper>
);

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
      {status.is_running ? (
        <InstanceDashboard instanceId={instanceId} />
      ) : (
        <NotRunning />
      )}
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
