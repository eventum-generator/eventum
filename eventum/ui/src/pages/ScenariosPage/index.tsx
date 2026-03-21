import {
  ActionIcon,
  Alert,
  Box,
  Button,
  Center,
  Container,
  Group,
  Loader,
  Paper,
  Stack,
  TextInput,
} from '@mantine/core';
import { modals } from '@mantine/modals';
import { IconAlertSquareRounded, IconSearch, IconX } from '@tabler/icons-react';
import { useMemo, useState } from 'react';

import { CreateScenarioModal } from './CreateScenarioModal';
import { ScenariosTable } from './ScenariosTable';
import { ScenarioRow } from './ScenariosTable/types';
import { useGenerators } from '@/api/hooks/useGenerators';
import { useStartupGenerators } from '@/api/hooks/useStartup';
import {
  GeneratorStatus,
  GeneratorsInfo,
} from '@/api/routes/generators/schemas';
import { StartupGeneratorParametersList } from '@/api/routes/startup/schemas';
import { PageTitle } from '@/components/ui/PageTitle';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';

function classifyStatus(status: GeneratorStatus | undefined) {
  if (!status) return 'stopped' as const;
  if (status.is_running) return 'running' as const;
  if (status.is_initializing) return 'initializing' as const;
  return 'stopped' as const;
}

function deriveScenarios(
  startupEntries: StartupGeneratorParametersList,
  generators: GeneratorsInfo
): ScenarioRow[] {
  const scenarioGenerators = new Map<string, string[]>();

  for (const entry of startupEntries) {
    for (const scenario of entry.scenarios ?? []) {
      const existing = scenarioGenerators.get(scenario) ?? [];
      existing.push(entry.id);
      scenarioGenerators.set(scenario, existing);
    }
  }

  const generatorStatusMap = new Map(generators.map((g) => [g.id, g.status]));

  const rows: ScenarioRow[] = [];

  for (const [name, generatorIds] of scenarioGenerators) {
    let runningCount = 0;
    let stoppedCount = 0;
    let initializingCount = 0;

    for (const id of generatorIds) {
      const classification = classifyStatus(generatorStatusMap.get(id));
      if (classification === 'running') runningCount++;
      else if (classification === 'initializing') initializingCount++;
      else stoppedCount++;
    }

    rows.push({
      name,
      generatorCount: generatorIds.length,
      runningCount,
      stoppedCount,
      initializingCount,
    });
  }

  return rows.sort((a, b) => a.name.localeCompare(b.name));
}

export default function ScenariosPage() {
  const [nameFilter, setNameFilter] = useState('');

  const {
    data: startupEntries,
    isLoading: isStartupLoading,
    isError: isStartupError,
    error: startupError,
  } = useStartupGenerators();

  const {
    data: generators,
    isLoading: isGeneratorsLoading,
    isError: isGeneratorsError,
    error: generatorsError,
  } = useGenerators();

  const isLoading = isStartupLoading || isGeneratorsLoading;
  const isError = isStartupError || isGeneratorsError;
  const error = startupError ?? generatorsError;

  const scenarios = useMemo(() => {
    if (!startupEntries || !generators) {
      return [];
    }
    return deriveScenarios(startupEntries, generators);
  }, [startupEntries, generators]);

  if (isLoading) {
    return (
      <Center>
        <Loader size="lg" />
      </Center>
    );
  }

  if (isError) {
    return (
      <Container size="md" mt="lg">
        <PageTitle title="Scenarios" />
        <Alert
          variant="default"
          icon={<Box c="red" component={IconAlertSquareRounded}></Box>}
          title="Failed to load scenarios"
        >
          {error?.message}
          {error && <ShowErrorDetailsAnchor error={error} prependDot />}
        </Alert>
      </Container>
    );
  }

  return (
    <Container size="100%">
      <Stack>
        <PageTitle title="Scenarios" />

        <Paper withBorder p="sm">
          <Group justify="space-between">
            <Group>
              <TextInput
                leftSection={<IconSearch size={16} />}
                rightSection={
                  <ActionIcon
                    variant="transparent"
                    onClick={() => setNameFilter('')}
                    data-input-section
                  >
                    <IconX size={16} />
                  </ActionIcon>
                }
                placeholder="search by name..."
                value={nameFilter}
                onChange={(event) => setNameFilter(event.target.value)}
              />
            </Group>
            <Button
              onClick={() =>
                modals.open({
                  title: 'Create scenario',
                  children: <CreateScenarioModal />,
                })
              }
            >
              Create new
            </Button>
          </Group>
        </Paper>

        <ScenariosTable
          data={scenarios}
          nameFilter={nameFilter}
          startupEntries={startupEntries ?? []}
        />
      </Stack>
    </Container>
  );
}
