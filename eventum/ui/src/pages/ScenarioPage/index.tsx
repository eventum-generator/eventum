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
  TextInput,
  Title,
} from '@mantine/core';
import { modals } from '@mantine/modals';
import { notifications } from '@mantine/notifications';
import {
  IconAlertSquareRounded,
  IconArrowLeft,
  IconLayersSubtract,
  IconPlayerPlay,
  IconPlayerStop,
  IconPlus,
  IconServer,
} from '@tabler/icons-react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useCallback, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

import { AddGeneratorModal } from './AddGeneratorModal';
import { DataFlowDiagram } from './DataFlowDiagram';
import { GeneratorCard } from './GeneratorCard';
import { GlobalStatePanel } from './GlobalStatePanel';
import { useGenerators } from '@/api/hooks/useGenerators';
import { useMultiGlobalsUsage } from '@/api/hooks/useScenarios';
import { useStartupGenerators } from '@/api/hooks/useStartup';
import {
  bulkStartGenerators,
  bulkStopGenerators,
} from '@/api/routes/generators';
import { GeneratorStatus } from '@/api/routes/generators/schemas';
import { updateGeneratorInStartup } from '@/api/routes/startup';
import { StartupGeneratorParameters } from '@/api/routes/startup/schemas';
import { PageTitle } from '@/components/ui/PageTitle';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';
import { ROUTE_PATHS } from '@/routing/paths';

export default function ScenarioPage() {
  const { scenarioName: rawScenarioName } = useParams<{
    scenarioName: string;
  }>();
  const scenarioName = decodeURIComponent(rawScenarioName ?? '');
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const [isEditing, setIsEditing] = useState(false);
  const [editName, setEditName] = useState(scenarioName);
  const [selectedGlobalKey, setSelectedGlobalKey] = useState<string | null>(null);
  const [highlightedNodeId, setHighlightedNodeId] = useState<string | null>(null);
  const [highlightedEdgeId, setHighlightedEdgeId] = useState<string | null>(null);
  const [expandedCardId, setExpandedCardId] = useState<string | null>(null);
  const isRenaming = useRef(false);

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

  const generatorPathMap = useMemo(() => {
    const map = new Map<string, string>();
    for (const entry of scenarioEntries) {
      map.set(entry.id, entry.path);
    }
    return map;
  }, [scenarioEntries]);

  const globalsUsageQueries = useMultiGlobalsUsage(scenarioGeneratorIds);

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

  const allGlobalKeys = useMemo(() => {
    const keys = new Set<string>();
    for (const usage of globalsUsageMap.values()) {
      if (!usage) continue;
      for (const ref of usage.writes) keys.add(ref.key);
      for (const ref of usage.reads) keys.add(ref.key);
    }
    return keys;
  }, [globalsUsageMap]);

  const handleStartEdit = useCallback(() => {
    setIsEditing(true);
    setEditName(scenarioName);
  }, [scenarioName]);

  const handleRename = useCallback(async () => {
    if (isRenaming.current) return;

    const trimmed = editName.trim();
    if (trimmed === scenarioName || !trimmed) {
      setIsEditing(false);
      return;
    }

    isRenaming.current = true;
    try {
      for (const entry of scenarioEntries) {
        const newScenarios = (entry.scenarios ?? []).map((s) =>
          s === scenarioName ? trimmed : s
        );
        await updateGeneratorInStartup(entry.id, {
          ...entry,
          scenarios: newScenarios,
        });
      }
      await queryClient.invalidateQueries({ queryKey: ['startup'] });
      notifications.show({
        title: 'Renamed',
        message: `Scenario renamed to "${trimmed}"`,
        color: 'green',
      });
      void navigate(`/scenarios/${encodeURIComponent(trimmed)}`, {
        replace: true,
      });
    } catch (error) {
      notifications.show({
        title: 'Error',
        message: (
          <>
            Failed to rename scenario
            {error instanceof Error && (
              <ShowErrorDetailsAnchor error={error} prependDot />
            )}
          </>
        ),
        color: 'red',
      });
    } finally {
      isRenaming.current = false;
      setIsEditing(false);
    }
  }, [editName, scenarioName, scenarioEntries, queryClient, navigate]);

  const handleCancelEdit = useCallback(() => {
    setIsEditing(false);
    setEditName(scenarioName);
  }, [scenarioName]);

  const bulkStart = useMutation({
    mutationFn: ({ ids }: { ids: string[] }) => bulkStartGenerators(ids),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['generators'] });
      notifications.show({
        title: 'Success',
        message: 'All scenario instances started',
        color: 'green',
      });
    },
    onError: (error) => {
      notifications.show({
        title: 'Error',
        message: (
          <>
            Failed to start instances
            <ShowErrorDetailsAnchor error={error} prependDot />
          </>
        ),
        color: 'red',
      });
    },
  });

  const bulkStop = useMutation({
    mutationFn: ({ ids }: { ids: string[] }) => bulkStopGenerators(ids),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['generators'] });
      notifications.show({
        title: 'Success',
        message: 'All scenario instances stopped',
        color: 'green',
      });
    },
    onError: (error) => {
      notifications.show({
        title: 'Error',
        message: (
          <>
            Failed to stop instances
            <ShowErrorDetailsAnchor error={error} prependDot />
          </>
        ),
        color: 'red',
      });
    },
  });

  const removeFromScenario = useMutation({
    mutationFn: async ({ entry }: { entry: StartupGeneratorParameters }) => {
      const updatedScenarios = (entry.scenarios ?? []).filter(
        (s) => s !== scenarioName
      );
      await updateGeneratorInStartup(entry.id, {
        ...entry,
        scenarios: updatedScenarios,
      });
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['startup'] });
      notifications.show({
        title: 'Success',
        message: 'Instance removed from scenario',
        color: 'green',
      });
    },
    onError: (error) => {
      notifications.show({
        title: 'Error',
        message: (
          <>
            Failed to remove instance
            <ShowErrorDetailsAnchor error={error} prependDot />
          </>
        ),
        color: 'red',
      });
    },
  });

  function handleRemoveGenerator(entry: StartupGeneratorParameters) {
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
        removeFromScenario.mutate({ entry });
      },
    });
  }

  function handleStartAll() {
    bulkStart.mutate({ ids: scenarioGeneratorIds });
  }

  function handleStopAll() {
    bulkStop.mutate({ ids: scenarioGeneratorIds });
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
    document.getElementById(`instance-card-${instanceId}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

  function handleDiagramKeyClick(keyName: string) {
    setSelectedGlobalKey(keyName);
  }

  function handleCardHover(nodeId: string | null) {
    setHighlightedNodeId(nodeId);
  }

  function handleKeyHover(keyName: string | null) {
    setHighlightedNodeId(keyName ? `key-${keyName}` : null);
  }

  function handleHighlightEdge(generatorId: string, keyName: string, direction?: 'write' | 'read') {
    if (generatorId && keyName) {
      setHighlightedNodeId(`key-${keyName}`);
      const prefix = direction ?? 'write';
      setHighlightedEdgeId(`${prefix}-${generatorId}-${keyName}`);
    } else {
      setHighlightedNodeId(null);
      setHighlightedEdgeId(null);
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
          {isEditing ? (
            <TextInput
              value={editName}
              onChange={(e) => setEditName(e.currentTarget.value)}
              onBlur={() => void handleRename()}
              onKeyDown={(e) => {
                if (e.key === 'Enter') void handleRename();
                if (e.key === 'Escape') handleCancelEdit();
              }}
              // eslint-disable-next-line jsx-a11y/no-autofocus -- intentional for inline rename UX
              autoFocus
              size="lg"
              styles={{
                input: { fontSize: 'var(--mantine-h2-font-size)', fontWeight: 400 },
              }}
              style={{ maxWidth: 400 }}
            />
          ) : (
            <Title
              order={2}
              fw="normal"
              style={{ cursor: 'pointer' }}
              onClick={handleStartEdit}
            >
              {scenarioName}
            </Title>
          )}
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
                  <IconServer size={18} />
                  <Title order={5} fw="normal">Instances</Title>
                </Group>
                <Button
                  variant="default"
                  size="xs"
                  leftSection={<IconPlus size={14} />}
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
                {allGlobalKeys.size > 0 && (
                  <DataFlowDiagram
                    scenarioEntries={scenarioEntries}
                    generatorStatusMap={generatorStatusMap}
                    globalsUsageMap={globalsUsageMap}
                    highlightedNodeId={highlightedNodeId}
                    highlightedEdgeId={highlightedEdgeId}
                    onInstanceClick={handleDiagramInstanceClick}
                    onKeyClick={handleDiagramKeyClick}
                  />
                )}
                <Paper withBorder p="md">
                  <Stack gap="sm">
                    <Group justify="space-between" align="center">
                      <Group gap="sm" align="center">
                        <Group gap="xs">
                          <IconServer size={18} />
                          <Title order={5} fw="normal">Instances</Title>
                        </Group>
                        <Text size="xs" c="dimmed">
                          {scenarioEntries.length} instance{scenarioEntries.length !== 1 ? 's' : ''}
                        </Text>
                      </Group>
                      <Group gap="xs">
                        <Button
                          variant="default"
                          size="xs"
                          leftSection={<IconPlus size={14} />}
                          onClick={handleOpenAddModal}
                        >
                          Add
                        </Button>
                        <Button
                          variant="default"
                          size="xs"
                          leftSection={<IconPlayerStop size={14} />}
                          onClick={handleStopAll}
                          loading={bulkStop.isPending}
                          disabled={scenarioGeneratorIds.length === 0}
                        >
                          Stop All
                        </Button>
                        <Button
                          variant="default"
                          size="xs"
                          leftSection={<IconPlayerPlay size={14} />}
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
                            onHover={handleCardHover}
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
              <GlobalStatePanel
                generatorNames={scenarioGeneratorIds}
                generatorPaths={generatorPathMap}
                globalsUsageResults={globalsUsageQueries}
                selectedKey={selectedGlobalKey}
                onKeyHover={handleKeyHover}
              />
            </Grid.Col>
          </Grid>
        )}
      </Stack>
    </Container>
  );
}
