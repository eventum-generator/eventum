import {
  Alert,
  Box,
  Button,
  Center,
  Container,
  Grid,
  Group,
  Loader,
  Paper,
  Stack,
  Text,
  Title,
} from '@mantine/core';
import { modals } from '@mantine/modals';
import {
  IconAlertSquareRounded,
  IconArrowLeft,
  IconLayersSubtract,
  IconPlayerPlay,
  IconPlayerStop,
  IconPlus,
} from '@tabler/icons-react';
import { useCallback, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

import { AddGeneratorModal } from './AddGeneratorModal';
import { DataFlowDiagram } from './DataFlowDiagram';
import { collectGlobalKeys } from './globals-usage';
import { GeneratorCard } from './GeneratorCard';
import { GlobalStatePanel } from './GlobalStatePanel';
import { useHighlightState } from './useHighlightState';
import { useScenarioBulkActions } from './useScenarioBulkActions';
import {
  useGenerators,
  useUpdateGeneratorStatus,
} from '@/api/hooks/useGenerators';
import {
  useMultiGlobalsUsage,
  useRemoveGeneratorFromScenarioMutation,
} from '@/api/hooks/useScenarios';
import { useStartupGenerators } from '@/api/hooks/useStartup';
import { GeneratorStatus } from '@/api/routes/generators/schemas';
import { StartupGeneratorParameters } from '@/api/routes/startup/schemas';
import { PageTitle } from '@/components/ui/PageTitle';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';
import { ROUTE_PATHS } from '@/routing/paths';
import {
  showErrorNotification,
  showSuccessNotification,
} from '@/utils/notifications';

export default function ScenarioPage() {
  const { scenarioName: rawScenarioName } = useParams<{
    scenarioName: string;
  }>();
  const scenarioName = decodeURIComponent(rawScenarioName ?? '');
  const navigate = useNavigate();

  const { highlightedNodeId, highlightedEdgeId, highlightNode, highlightEdge } = useHighlightState();
  const [expandedCardId, setExpandedCardId] = useState<string | null>(null);

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

  const scenarioEntries = useMemo(() => {
    if (!startupEntries) return [];
    return startupEntries.filter((entry) =>
      (entry.scenarios ?? []).includes(scenarioName)
    );
  }, [startupEntries, scenarioName]);

  const scenarioGeneratorIds = useMemo(
    () => scenarioEntries.map((entry) => entry.id),
    [scenarioEntries]
  );

  const globalsUsageQueries = useMultiGlobalsUsage(scenarioName, scenarioGeneratorIds);

  const globalsUsageMap = useMemo(() => {
    const map = new Map<string, (typeof globalsUsageQueries)[number]['data']>();
    for (const [i, generatorId] of scenarioGeneratorIds.entries()) {
      const query = globalsUsageQueries[i];
      if (query?.data) {
        map.set(generatorId, query.data);
      }
    }
    return map;
  }, [scenarioGeneratorIds, globalsUsageQueries]);

  const generatorStatusMap = useMemo(() => {
    if (!generators) return new Map<string, GeneratorStatus>();
    return new Map(generators.map((g) => [g.id, g.status]));
  }, [generators]);

  const hasGlobalKeys = useMemo(
    () => collectGlobalKeys(globalsUsageMap).length > 0,
    [globalsUsageMap],
  );

  const { bulkStart, bulkStop } = useScenarioBulkActions(scenarioGeneratorIds);
  const updateStatus = useUpdateGeneratorStatus();
  const removeFromScenario = useRemoveGeneratorFromScenarioMutation();

  const handleRemoveGenerator = useCallback((entry: StartupGeneratorParameters) => {
    modals.openConfirmModal({
      title: 'Remove from scenario',
      children: (
        <Text size="sm">
          Remove <b>{entry.id}</b> from scenario <b>{scenarioName}</b>? The
          instance will not be deleted.
        </Text>
      ),
      labels: { cancel: 'Cancel', confirm: 'Remove' },
      onConfirm: () => {
        removeFromScenario.mutate(
          { name: scenarioName, generatorId: entry.id },
          {
            onSuccess: () =>
              showSuccessNotification('Success', 'Instance removed from scenario'),
            onError: (error) =>
              showErrorNotification('Failed to remove instance', error),
          },
        );
      },
    });
  }, [scenarioName, removeFromScenario]);

  function handleStartAll() {
    for (const id of scenarioGeneratorIds) {
      const current = generatorStatusMap.get(id);
      if (current && !current.is_running && !current.is_initializing) {
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
    }
    bulkStart.mutate(
      { ids: scenarioGeneratorIds },
      {
        onSuccess: () => showSuccessNotification('Success', 'All scenario instances started'),
        onError: (e) => showErrorNotification('Failed to start instances', e),
      },
    );
  }

  function handleStopAll() {
    for (const id of scenarioGeneratorIds) {
      const current = generatorStatusMap.get(id);
      if (current?.is_running) {
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
    }
    bulkStop.mutate(
      { ids: scenarioGeneratorIds },
      {
        onSuccess: () => showSuccessNotification('Success', 'All scenario instances stopped'),
        onError: (e) => showErrorNotification('Failed to stop instances', e),
      },
    );
  }

  function handleOpenAddModal() {
    modals.open({
      title: 'Add instance to scenario',
      children: <AddGeneratorModal scenarioName={scenarioName} />,
      size: 'lg',
    });
  }

  function handleDiagramInstanceClick(instanceId: string) {
    setExpandedCardId(instanceId);
    document.querySelector(`#instance-card-${CSS.escape(instanceId)}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

  function handleHighlightEdge(generatorId: string, keyName: string, direction?: 'write' | 'read') {
    if (generatorId && keyName) {
      const prefix = direction ?? 'write';
      highlightEdge(`${prefix}-${generatorId}-${keyName}`);
    } else {
      highlightEdge(null);
    }
  }

  const isLoading = isStartupLoading || isGeneratorsLoading;
  const isError = isStartupError || isGeneratorsError;
  const error = startupError ?? generatorsError;

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
        <PageTitle title="Scenario" />
        <Alert
          variant="default"
          icon={<Box c="red" component={IconAlertSquareRounded}></Box>}
          title="Failed to load scenario"
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
        <Group justify="space-between" align="center">
          <Title order={3} fw="bold">
            {scenarioName}
          </Title>
          <Button
            variant="default"
            leftSection={<IconArrowLeft size={16} />}
            onClick={() => void navigate(ROUTE_PATHS.SCENARIOS)}
          >
            Back
          </Button>
        </Group>

        {scenarioEntries.length === 0 ? (
          <Paper withBorder p="md">
            <Stack gap="sm">
              <Group justify="space-between" align="center">
                <Group gap="xs">
                  <IconPlayerPlay size={18} />
                  <Title order={5} fw="normal">Instances</Title>
                </Group>
                <Button
                  variant="default"
                  leftSection={<IconPlus size={16} />}
                  onClick={handleOpenAddModal}
                >
                  Add
                </Button>
              </Group>
              <Center py="xl">
                <Stack align="center" gap="md">
                  <IconLayersSubtract size={48} color="gray" />
                  <Text c="dimmed" ta="center">
                    Add your first instances to build a scenario
                  </Text>
                </Stack>
              </Center>
            </Stack>
          </Paper>
        ) : (
          <Grid>
            <Grid.Col span={7}>
              <Stack>
                {hasGlobalKeys && (
                  <DataFlowDiagram
                    scenarioEntries={scenarioEntries}
                    generatorStatusMap={generatorStatusMap}
                    globalsUsageMap={globalsUsageMap}
                    highlightedNodeId={highlightedNodeId}
                    highlightedEdgeId={highlightedEdgeId}
                    onInstanceClick={handleDiagramInstanceClick}
                  />
                )}
                <Paper withBorder p="md">
                  <Stack gap="sm">
                    <Group justify="space-between" align="center">
                      <Group gap="sm" align="center">
                        <Group gap="xs">
                          <IconPlayerPlay size={18} />
                          <Title order={5} fw="normal">Instances</Title>
                        </Group>
                        <Text size="xs" c="dimmed">
                          {scenarioEntries.length} instance{scenarioEntries.length !== 1 ? 's' : ''}
                        </Text>
                      </Group>
                      <Group gap="xs">
                        <Button
                          variant="default"
                          leftSection={<IconPlus size={16} />}
                          onClick={handleOpenAddModal}
                        >
                          Add
                        </Button>
                        <Button
                          variant="default"
                          leftSection={<IconPlayerStop size={16} />}
                          onClick={handleStopAll}
                          loading={bulkStop.isPending}
                          disabled={scenarioGeneratorIds.length === 0}
                        >
                          Stop All
                        </Button>
                        <Button
                          variant="default"
                          leftSection={<IconPlayerPlay size={16} />}
                          onClick={handleStartAll}
                          loading={bulkStart.isPending}
                          disabled={scenarioGeneratorIds.length === 0}
                        >
                          Start All
                        </Button>
                      </Group>
                    </Group>
                    <Stack gap="sm">
                      {scenarioEntries.map((entry) => (
                        <div key={entry.id} id={`instance-card-${entry.id}`}>
                          <GeneratorCard
                            generatorId={entry.id}
                            generatorPath={entry.path}
                            status={generatorStatusMap.get(entry.id)}
                            globalsUsage={globalsUsageMap.get(entry.id)}
                            isExpanded={expandedCardId === entry.id}
                            onToggleExpand={() =>
                              setExpandedCardId((prev) =>
                                prev === entry.id ? null : entry.id
                              )
                            }
                            onRemove={() => handleRemoveGenerator(entry)}
                            onHover={highlightNode}
                            onHighlightEdge={handleHighlightEdge}
                          />
                        </div>
                      ))}
                    </Stack>
                  </Stack>
                </Paper>
              </Stack>
            </Grid.Col>
            <Grid.Col span={5}>
              <GlobalStatePanel scenarioName={scenarioName} />
            </Grid.Col>
          </Grid>
        )}
      </Stack>
    </Container>
  );
}
