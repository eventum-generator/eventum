import {
  ActionIcon,
  Alert,
  Box,
  Button,
  Center,
  Container,
  Group,
  List,
  Loader,
  Paper,
  SegmentedControl,
  Stack,
  Text,
  TextInput,
} from '@mantine/core';
import { modals } from '@mantine/modals';
import {
  IconPlayerPlay,
  IconPlayerStop,
  IconRefresh,
  IconSearch,
  IconTrash,
  IconX,
} from '@tabler/icons-react';
import { RowSelectionState } from '@tanstack/react-table';
import { useCallback, useMemo, useRef, useState } from 'react';

import { CreateScenarioModal } from './CreateScenarioModal';
import { ScenariosEmptyState } from './ScenariosEmptyState';
import { ScenarioStatusMode, ScenariosTable } from './ScenariosTable';
import { ScenarioRow } from './ScenariosTable/types';
import {
  useBulkStartGeneratorMutation,
  useBulkStopGeneratorMutation,
  useGenerators,
  useUpdateGeneratorStatus,
} from '@/api/hooks/useGenerators';
import { useDeleteScenarioMutation } from '@/api/hooks/useScenarios';
import { useStartupGenerators } from '@/api/hooks/useStartup';
import { GeneratorsInfo } from '@/api/routes/generators/schemas';
import { StartupGeneratorParametersList } from '@/api/routes/startup/schemas';
import { AlertIcon } from '@/components/ui/AlertIcon';
import { PageTitle } from '@/components/ui/PageTitle';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';
import { scenarioStatusBucket } from '@/components/ui/statusPalette';
import {
  showErrorNotification,
  showSuccessNotification,
} from '@/utils/notifications';
import { useTableQueryParams } from '@/utils/useTableQueryParams';

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
      const classification = scenarioStatusBucket(generatorStatusMap.get(id));
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
  const { searchParams, setParams } = useTableQueryParams();
  const nameFilter = searchParams.get('q') ?? '';
  const rawStatus = searchParams.get('status');
  const statusMode: ScenarioStatusMode =
    rawStatus === 'running' || rawStatus === 'idle' ? rawStatus : 'all';

  const [rowSelection, setRowSelection] = useState<RowSelectionState>({});
  const [refreshTurns, setRefreshTurns] = useState(0);

  const {
    data: startupEntries,
    isLoading: isStartupLoading,
    isError: isStartupError,
    error: startupError,
    refetch: refetchStartup,
  } = useStartupGenerators();

  const {
    data: generators,
    isLoading: isGeneratorsLoading,
    isError: isGeneratorsError,
    error: generatorsError,
    refetch: refetchGenerators,
  } = useGenerators();

  const isLoading = isStartupLoading || isGeneratorsLoading;
  const isError = isStartupError || isGeneratorsError;
  const error = startupError ?? generatorsError;

  const bulkStart = useBulkStartGeneratorMutation();
  const bulkStop = useBulkStopGeneratorMutation();
  const updateStatus = useUpdateGeneratorStatus();
  const deleteScenario = useDeleteScenarioMutation();

  const scenarios = useMemo(() => {
    if (!startupEntries || !generators) {
      return [];
    }
    return deriveScenarios(startupEntries, generators);
  }, [startupEntries, generators]);

  // Keep the latest scenarios in a ref so getAffectedScenarios stays a stable
  // callback. If its identity changed per fetch, the table columns (built from
  // it) would rebuild every render, remounting the InstanceBadges cells and
  // refetching generators in a loop (useGenerators has no staleTime).
  const scenariosRef = useRef(scenarios);
  scenariosRef.current = scenarios;

  const getAffectedScenarios = useCallback(
    (scenarioName: string, generatorIds: string[]) => {
      const affected: string[] = [];
      for (const row of scenariosRef.current) {
        if (row.name === scenarioName) continue;
        if (row.generatorIds.some((id) => generatorIds.includes(id))) {
          affected.push(row.name);
        }
      }
      return affected;
    },
    []
  );

  // Row ids are the scenario names (via getRowId in the table), so the
  // selection keys are names directly - map them back and drop any that no
  // longer exist.
  const selectedScenarios = useMemo(() => {
    const byName = new Map(scenarios.map((row) => [row.name, row]));
    return Object.keys(rowSelection)
      .map((name) => byName.get(name))
      .filter((row): row is ScenarioRow => row !== undefined);
  }, [rowSelection, scenarios]);

  const selectedGeneratorIds = useMemo(() => {
    return selectedScenarios.flatMap((row) => row.generatorIds);
  }, [selectedScenarios]);

  function handleBulkDelete() {
    const names = selectedScenarios.map((s) => s.name);
    modals.openConfirmModal({
      title: 'Delete scenarios',
      children: (
        <Text size="sm">
          Delete {names.length} scenario(s): <b>{names.join(', ')}</b>?
          Instances will not be deleted.
        </Text>
      ),
      labels: { cancel: 'Cancel', confirm: 'Delete' },
      onConfirm: () => {
        for (const name of names) {
          deleteScenario.mutate(name, {
            onError: (e) =>
              showErrorNotification(`Failed to delete "${name}"`, e),
          });
        }
        setRowSelection({});
        showSuccessNotification(
          'Deleted',
          `${names.length} scenario(s) deleted`
        );
      },
    });
  }

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
        onError: (e) => showErrorNotification('Failed to start scenarios', e),
      }
    );
  }

  function executeBulkStop() {
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
        onError: (e) => showErrorNotification('Failed to stop scenarios', e),
      }
    );
  }

  function handleBulkStop() {
    const selectedNames = new Set(selectedScenarios.map((s) => s.name));
    const affected = new Set<string>();
    for (const name of selectedNames) {
      const row = scenarios.find((s) => s.name === name);
      if (!row) continue;
      for (const other of getAffectedScenarios(name, row.generatorIds)) {
        if (!selectedNames.has(other)) affected.add(other);
      }
    }

    if (affected.size > 0) {
      modals.openConfirmModal({
        title: 'Shared instances detected',
        children: (
          <Text size="sm">
            Some instances are also used in other scenarios. Stopping them will
            affect:
            <List size="sm" mt="xs">
              {[...affected].map((name) => (
                <List.Item key={name}>
                  <b>{name}</b>
                </List.Item>
              ))}
            </List>
          </Text>
        ),
        labels: { cancel: 'Cancel', confirm: 'Stop anyway' },
        onConfirm: executeBulkStop,
      });
    } else {
      executeBulkStop();
    }
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
          icon={<AlertIcon variant="error" />}
          title="Failed to load scenarios"
        >
          {error?.message}
          {error && <ShowErrorDetailsAnchor error={error} prependDot />}
        </Alert>
      </Container>
    );
  }

  const openCreateModal = () =>
    modals.open({
      title: 'Create scenario',
      children: <CreateScenarioModal />,
      size: 'lg',
    });

  const total = scenarios.length;

  if (total === 0) {
    return (
      <Container size="100%">
        <Stack>
          <PageTitle title="Scenarios" />
          <ScenariosEmptyState onCreate={openCreateModal} />
        </Stack>
      </Container>
    );
  }

  const active = scenarios.filter((row) => row.runningCount > 0).length;
  const hasSelection = selectedScenarios.length > 0;

  return (
    <Container size="100%">
      <Stack>
        <Group align="baseline" gap="sm">
          <PageTitle title="Scenarios" />
          <Text size="sm" c="dimmed">
            {total} {total === 1 ? 'scenario' : 'scenarios'} · {active} active
          </Text>
        </Group>

        <Paper withBorder p="sm">
          <Group justify="space-between">
            <Group>
              <TextInput
                leftSection={<IconSearch size={16} />}
                rightSection={
                  <ActionIcon
                    variant="transparent"
                    onClick={() => setParams({ q: null })}
                    data-input-section
                  >
                    <IconX size={16} />
                  </ActionIcon>
                }
                placeholder="search by name..."
                value={nameFilter}
                onChange={(event) =>
                  setParams({ q: event.target.value || null })
                }
              />
              <SegmentedControl
                value={statusMode}
                onChange={(value) =>
                  setParams({ status: value === 'all' ? null : value })
                }
                data={[
                  { label: 'All', value: 'all' },
                  { label: 'Running', value: 'running' },
                  { label: 'Idle', value: 'idle' },
                ]}
              />
            </Group>
            <Group gap="sm">
              {hasSelection && (
                <Text size="sm" c="dimmed">
                  {selectedScenarios.length} selected
                </Text>
              )}
              <ActionIcon.Group>
                <ActionIcon
                  size="lg"
                  variant="default"
                  title="Start selected"
                  disabled={!hasSelection}
                  loading={bulkStart.isPending}
                  onClick={handleBulkStart}
                >
                  <IconPlayerPlay size={18} />
                </ActionIcon>
                <ActionIcon
                  size="lg"
                  variant="default"
                  title="Stop selected"
                  disabled={!hasSelection}
                  loading={bulkStop.isPending}
                  onClick={handleBulkStop}
                >
                  <IconPlayerStop size={18} />
                </ActionIcon>
                <ActionIcon
                  size="lg"
                  variant="default"
                  title="Delete selected"
                  disabled={!hasSelection}
                  onClick={handleBulkDelete}
                >
                  <Box c={hasSelection ? 'red' : undefined}>
                    <IconTrash size={18} />
                  </Box>
                </ActionIcon>
              </ActionIcon.Group>
              <ActionIcon
                size="lg"
                variant="default"
                title="Refresh"
                onClick={() => {
                  setRefreshTurns((turns) => turns + 1);
                  void refetchGenerators();
                  void refetchStartup();
                }}
              >
                <IconRefresh
                  size={18}
                  style={{
                    transition:
                      'transform 0.65s cubic-bezier(0.22, 1, 0.36, 1)',
                    transform: `rotate(${refreshTurns * 360}deg)`,
                  }}
                />
              </ActionIcon>
              <Button onClick={openCreateModal}>Create new</Button>
            </Group>
          </Group>
        </Paper>

        <ScenariosTable
          data={scenarios}
          nameFilter={nameFilter}
          statusMode={statusMode}
          rowSelection={rowSelection}
          onRowSelectionChange={setRowSelection}
          getAffectedScenarios={getAffectedScenarios}
        />
      </Stack>
    </Container>
  );
}
