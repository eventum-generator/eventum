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
  Tooltip,
} from '@mantine/core';
import { modals } from '@mantine/modals';
import {
  IconAlertSquareRounded,
  IconPlayerPlay,
  IconPlayerStop,
  IconSearch,
  IconX,
} from '@tabler/icons-react';
import { RowSelectionState } from '@tanstack/react-table';
import { useMemo, useState } from 'react';

import { CreateScenarioModal } from './CreateScenarioModal';
import { ScenariosTable } from './ScenariosTable';
import { ScenarioRow } from './ScenariosTable/types';
import {
  useBulkStartGeneratorMutation,
  useBulkStopGeneratorMutation,
  useGenerators,
  useUpdateGeneratorStatus,
} from '@/api/hooks/useGenerators';
import { useStartupGenerators } from '@/api/hooks/useStartup';
import {
  GeneratorStatus,
  GeneratorsInfo,
} from '@/api/routes/generators/schemas';
import { StartupGeneratorParametersList } from '@/api/routes/startup/schemas';
import { PageTitle } from '@/components/ui/PageTitle';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';
import {
  showErrorNotification,
  showSuccessNotification,
} from '@/utils/notifications';

function classifyStatus(status: GeneratorStatus | undefined) {
  if (!status) return 'stopped' as const;
  if (status.is_initializing) return 'initializing' as const;
  if (status.is_stopping) return 'stopping' as const;
  if (status.is_running) return 'running' as const;
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
    let stoppingCount = 0;

    for (const id of generatorIds) {
      const classification = classifyStatus(generatorStatusMap.get(id));
      if (classification === 'running') runningCount++;
      else if (classification === 'initializing') initializingCount++;
      else if (classification === 'stopping') stoppingCount++;
      else stoppedCount++;
    }

    rows.push({
      name,
      generatorIds,
      generatorCount: generatorIds.length,
      runningCount,
      stoppedCount,
      initializingCount,
      stoppingCount,
    });
  }

  return rows.sort((a, b) => a.name.localeCompare(b.name));
}

export default function ScenariosPage() {
  const [nameFilter, setNameFilter] = useState('');
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({});

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

  const bulkStart = useBulkStartGeneratorMutation();
  const bulkStop = useBulkStopGeneratorMutation();
  const updateStatus = useUpdateGeneratorStatus();

  const scenarios = useMemo(() => {
    if (!startupEntries || !generators) {
      return [];
    }
    return deriveScenarios(startupEntries, generators);
  }, [startupEntries, generators]);

  const selectedGeneratorIds = useMemo(() => {
    const ids: string[] = [];
    for (const rowId of Object.keys(rowSelection)) {
      const row = scenarios[Number(rowId)];
      if (row) ids.push(...row.generatorIds);
    }
    return ids;
  }, [rowSelection, scenarios]);

  function handleBulkStart() {
    for (const id of selectedGeneratorIds) {
      updateStatus.mutate({
        id,
        status: {
          is_initializing: true,
          is_running: false,
          is_stopping: false,
          is_ended_up: false,
          is_ended_up_successfully: false,
        },
      });
    }
    bulkStart.mutate(
      { ids: selectedGeneratorIds },
      {
        onSuccess: () =>
          showSuccessNotification('Success', 'Selected scenarios started'),
        onError: (e) =>
          showErrorNotification('Failed to start scenarios', e),
      },
    );
  }

  function handleBulkStop() {
    for (const id of selectedGeneratorIds) {
      updateStatus.mutate({
        id,
        status: {
          is_initializing: false,
          is_running: false,
          is_stopping: true,
          is_ended_up: false,
          is_ended_up_successfully: false,
        },
      });
    }
    bulkStop.mutate(
      { ids: selectedGeneratorIds },
      {
        onSuccess: () =>
          showSuccessNotification('Success', 'Selected scenarios stopped'),
        onError: (e) =>
          showErrorNotification('Failed to stop scenarios', e),
      },
    );
  }

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
            <Group gap={0}>
              <Tooltip label="Stop selected">
                <ActionIcon
                  size="lg"
                  variant="default"
                  style={{ borderTopRightRadius: 0, borderBottomRightRadius: 0 }}
                  disabled={selectedGeneratorIds.length === 0}
                  loading={bulkStop.isPending}
                  onClick={handleBulkStop}
                >
                  <IconPlayerStop size={20} />
                </ActionIcon>
              </Tooltip>
              <Tooltip label="Start selected">
                <ActionIcon
                  size="lg"
                  variant="default"
                  style={{ borderTopLeftRadius: 0, borderBottomLeftRadius: 0 }}
                  disabled={selectedGeneratorIds.length === 0}
                  loading={bulkStart.isPending}
                  onClick={handleBulkStart}
                >
                  <IconPlayerPlay size={20} />
                </ActionIcon>
              </Tooltip>
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
          rowSelection={rowSelection}
          onRowSelectionChange={setRowSelection}
        />
      </Stack>
    </Container>
  );
}
