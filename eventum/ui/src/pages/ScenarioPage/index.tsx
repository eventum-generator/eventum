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
  IconLayersSubtract,
  IconPlayerPlay,
  IconPlayerStop,
  IconPlus,
} from '@tabler/icons-react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useCallback, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

import { AddGeneratorModal } from './AddGeneratorModal';
import { DataFlowDiagram } from './DataFlowDiagram';
import { GeneratorCard, InstanceFlowInfo } from './GeneratorCard';
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

export default function ScenarioPage() {
  const { scenarioName: rawScenarioName } = useParams<{
    scenarioName: string;
  }>();
  const scenarioName = decodeURIComponent(rawScenarioName ?? '');
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const [isEditing, setIsEditing] = useState(false);
  const [editName, setEditName] = useState(scenarioName);
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

  // Compute flow info for each instance
  const flowInfoMap = useMemo(() => {
    const map = new Map<string, InstanceFlowInfo>();

    // First, build a global index of who writes and reads each key
    const keyWriters = new Map<string, Set<string>>();
    const keyReaders = new Map<string, Set<string>>();

    for (const [generatorId, usage] of globalsUsageMap.entries()) {
      if (!usage) continue;

      for (const ref of usage.writes) {
        if (!keyWriters.has(ref.key)) keyWriters.set(ref.key, new Set());
        keyWriters.get(ref.key)!.add(generatorId);
      }

      for (const ref of usage.reads) {
        if (!keyReaders.has(ref.key)) keyReaders.set(ref.key, new Set());
        keyReaders.get(ref.key)!.add(generatorId);
      }
    }

    // Now compute provides/consumes for each instance
    for (const [generatorId, usage] of globalsUsageMap.entries()) {
      if (!usage) {
        map.set(generatorId, { provides: [], consumes: [], warnings: [] });
        continue;
      }

      const writtenKeys = new Set(usage.writes.map((w) => w.key));
      const readKeys = new Set(usage.reads.map((r) => r.key));
      const warnings: string[] = [];

      // Provides: keys this instance writes, with targets being OTHER instances that read them
      const provides = [...writtenKeys].map((key) => {
        const allReaders = keyReaders.get(key) ?? new Set();
        const targets = [...allReaders].filter((id) => id !== generatorId);

        if (targets.length === 0 && !readKeys.has(key)) {
          warnings.push(`${key} has no consumers`);
        }

        return { keyName: key, targets };
      });

      // Consumes: keys this instance reads, with sources being OTHER instances that write them
      const consumes = [...readKeys].map((key) => {
        const allWriters = keyWriters.get(key) ?? new Set();
        const sources = [...allWriters].filter((id) => id !== generatorId);

        if (sources.length === 0 && !writtenKeys.has(key)) {
          warnings.push(`${key} has no provider`);
        }

        return { keyName: key, sources };
      });

      // Filter out self-only loops (key is both written and read by only this instance)
      const filteredProvides = provides.filter((p) => {
        if (p.targets.length > 0) return true;
        // Keep if someone else reads it, or nobody reads it (warning case)
        const allReaders = keyReaders.get(p.keyName) ?? new Set();
        return allReaders.size === 0 || [...allReaders].some((id) => id !== generatorId);
      });

      const filteredConsumes = consumes.filter((c) => {
        if (c.sources.length > 0) return true;
        // Keep if someone else writes it, or nobody writes it (warning case)
        const allWriters = keyWriters.get(c.keyName) ?? new Set();
        return allWriters.size === 0 || [...allWriters].some((id) => id !== generatorId);
      });

      map.set(generatorId, {
        provides: filteredProvides,
        consumes: filteredConsumes,
        warnings,
      });
    }

    // For generators without usage data yet, set empty flow info
    for (const generatorId of scenarioGeneratorIds) {
      if (!map.has(generatorId)) {
        map.set(generatorId, { provides: [], consumes: [], warnings: [] });
      }
    }

    return map;
  }, [globalsUsageMap, scenarioGeneratorIds]);

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

        <Paper withBorder p="sm">
          <Group justify="space-between" align="center">
            <Text size="sm" c="dimmed">
              {scenarioEntries.length} instance
              {scenarioEntries.length !== 1 ? 's' : ''} &middot;{' '}
              {allGlobalKeys.size} global key
              {allGlobalKeys.size !== 1 ? 's' : ''}
            </Text>
            <Group gap="xs">
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
                leftSection={<IconPlayerPlay size={16} />}
                onClick={handleStartAll}
                loading={bulkStart.isPending}
                disabled={scenarioGeneratorIds.length === 0}
              >
                Start All
              </Button>
            </Group>
          </Group>
        </Paper>

        {scenarioEntries.length > 0 && allGlobalKeys.size > 0 && (
          <DataFlowDiagram
            scenarioEntries={scenarioEntries}
            generatorStatusMap={generatorStatusMap}
            globalsUsageMap={globalsUsageMap}
          />
        )}

        <Grid>
          <Grid.Col span={8}>
            <Paper withBorder p="md">
              <Stack gap="sm">
                <Group justify="space-between" align="center">
                  <Title order={5} fw="normal">
                    Instances
                  </Title>
                  <Button
                    variant="default"
                    size="xs"
                    leftSection={<IconPlus size={14} />}
                    onClick={handleOpenAddModal}
                  >
                    Add
                  </Button>
                </Group>

                {scenarioEntries.length === 0 ? (
                  <Center py="xl">
                    <Stack align="center" gap="md">
                      <IconLayersSubtract size={48} color="gray" />
                      <Text c="dimmed" ta="center">
                        Add your first instances to build a scenario
                      </Text>
                    </Stack>
                  </Center>
                ) : (
                  <Stack gap="sm">
                    {scenarioEntries.map((entry) => (
                      <GeneratorCard
                        key={entry.id}
                        generatorId={entry.id}
                        generatorPath={entry.path}
                        status={generatorStatusMap.get(entry.id)}
                        flowInfo={
                          flowInfoMap.get(entry.id) ?? {
                            provides: [],
                            consumes: [],
                            warnings: [],
                          }
                        }
                        onRemove={() => handleRemoveGenerator(entry)}
                      />
                    ))}
                  </Stack>
                )}
              </Stack>
            </Paper>
          </Grid.Col>

          <Grid.Col span={4}>
            <GlobalStatePanel
              generatorNames={scenarioGeneratorIds}
              generatorPaths={generatorPathMap}
              globalsUsageResults={globalsUsageQueries}
            />
          </Grid.Col>
        </Grid>
      </Stack>
    </Container>
  );
}
