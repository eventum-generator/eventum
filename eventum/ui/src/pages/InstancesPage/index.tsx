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
  SegmentedControl,
  Stack,
  Text,
  TextInput,
} from '@mantine/core';
import { modals } from '@mantine/modals';
import { notifications } from '@mantine/notifications';
import {
  IconPlayerPlay,
  IconPlayerStop,
  IconRefresh,
  IconSearch,
  IconTrash,
  IconX,
} from '@tabler/icons-react';
import { RowSelectionState } from '@tanstack/react-table';
import { useMemo, useState } from 'react';

import { CreateInstanceModal } from './CreateInstanceModal';
import { InstancesEmptyState } from './InstancesEmptyState';
import { InstancesTable, StatusMode } from './InstancesTable';
import {
  useBulkDeleteGeneratorMutation,
  useBulkStartGeneratorMutation,
  useBulkStopGeneratorMutation,
  useGenerators,
  useRunningGeneratorsStats,
  useUpdateGeneratorStatus,
} from '@/api/hooks/useGenerators';
import { useBulkDeleteGeneratorsFromStartupMutation } from '@/api/hooks/useStartup';
import { AlertIcon } from '@/components/ui/AlertIcon';
import { PageTitle } from '@/components/ui/PageTitle';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';
import { CONFIRM } from '@/theme/copy';
import { useTableQueryParams } from '@/utils/useTableQueryParams';

export default function InstancesPage() {
  const { searchParams, setParams } = useTableQueryParams();
  const instanceFilter = searchParams.get('instance') ?? '';
  const projectNameFilter = searchParams.get('project') ?? '';
  const rawStatus = searchParams.get('status');
  const statusMode: StatusMode =
    rawStatus === 'running' || rawStatus === 'inactive' ? rawStatus : 'all';

  const [rowSelection, setRowSelection] = useState<RowSelectionState>({});
  const [refreshTurns, setRefreshTurns] = useState(0);

  const {
    data: generators,
    isLoading: isGeneratorsLoading,
    isError: isGeneratorsError,
    error: generatorsError,
    isSuccess: isGeneratorsSuccess,
    refetch: refetchGenerators,
  } = useGenerators();

  const updateGeneratorStatus = useUpdateGeneratorStatus();
  const bulkStart = useBulkStartGeneratorMutation();
  const bulkStop = useBulkStopGeneratorMutation();
  const bulkDelete = useBulkDeleteGeneratorMutation();
  const bulkDeleteGeneratorsFromStartup =
    useBulkDeleteGeneratorsFromStartupMutation();

  // Stats are served only for running instances; fetched once and on manual
  // refresh (no auto-update), keyed by id for the table's Flow/Errors/Written
  // columns. Non-running instances have no entry and render "-".
  const { data: runningStats, refetch: refetchStats } =
    useRunningGeneratorsStats();

  const statsById = useMemo(
    () =>
      Object.fromEntries(
        (runningStats ?? []).map((stats) => [stats.id, stats])
      ),
    [runningStats]
  );

  function getInactiveInstances() {
    if (generators === undefined) {
      return [];
    }

    return generators
      .filter(
        (instance) =>
          !instance.status.is_running && !instance.status.is_initializing
      )
      .map((instance) => instance.id);
  }

  function getActiveInstances() {
    if (generators === undefined) {
      return [];
    }

    return generators
      .filter((instance) => instance.status.is_running)
      .map((instance) => instance.id);
  }

  function handleBulkStart(instanceIds: string[]) {
    const inactiveInstanceIds = getInactiveInstances();

    for (const instanceId of inactiveInstanceIds) {
      if (instanceIds.includes(instanceId)) {
        updateGeneratorStatus.mutate({
          id: instanceId,
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
      { ids: instanceIds },
      {
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
        onSuccess: (data) => {
          notifications.show({
            title: 'Success',
            message: `Started ${data.running_generator_ids.length} instances,
            ${data.non_running_generator_ids.length} failed to start`,
            color: 'green',
          });
        },
      }
    );
  }

  function handleBulkStop(instanceIds: string[]) {
    const activeInstanceIds = getActiveInstances();

    for (const instanceId of activeInstanceIds) {
      if (instanceIds.includes(instanceId)) {
        updateGeneratorStatus.mutate({
          id: instanceId,
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
      { ids: instanceIds },
      {
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
        onSuccess: () => {
          notifications.show({
            title: 'Success',
            message: `Instances are stopped`,
            color: 'green',
          });
        },
      }
    );
  }

  function handleBulkDelete(instanceIds: string[]) {
    const activeInstanceIds = getActiveInstances();

    for (const instanceId of activeInstanceIds) {
      if (instanceIds.includes(instanceId)) {
        updateGeneratorStatus.mutate({
          id: instanceId,
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

    bulkDelete.mutate(
      { ids: instanceIds },
      {
        onError: (error) => {
          notifications.show({
            title: 'Error',
            message: (
              <>
                Failed to delete instances
                <ShowErrorDetailsAnchor error={error} prependDot />
              </>
            ),
            color: 'red',
          });
        },
        onSuccess: () => {
          bulkDeleteGeneratorsFromStartup.mutate(
            { ids: instanceIds },
            {
              onSuccess: () => {
                setRowSelection({});
                notifications.show({
                  title: 'Success',
                  message: `Instances are deleted`,
                  color: 'green',
                });
              },
              onError: (error) => {
                notifications.show({
                  title: 'Error',
                  message: (
                    <>
                      Failed to delete instances definition from startup
                      <ShowErrorDetailsAnchor error={error} prependDot />
                    </>
                  ),
                  color: 'red',
                });
              },
            }
          );
        },
      }
    );
  }

  if (isGeneratorsLoading) {
    return (
      <Center>
        <Loader size="lg" />
      </Center>
    );
  }

  if (isGeneratorsError) {
    return (
      <Container size="md" mt="lg">
        <PageTitle title="Instances" />
        <Alert
          variant="default"
          icon={<AlertIcon variant="error" />}
          title="Failed to load instances list"
        >
          {generatorsError.message}
          <ShowErrorDetailsAnchor error={generatorsError} prependDot />
        </Alert>
      </Container>
    );
  }

  if (isGeneratorsSuccess) {
    const openCreateModal = () =>
      modals.open({
        title: 'New instance',
        children: (
          <CreateInstanceModal
            existingInstanceIds={generators.map((instance) => instance.id)}
          />
        ),
        size: 'lg',
      });

    const total = generators.length;

    if (total === 0) {
      return (
        <Container size="100%">
          <Stack>
            <PageTitle title="Instances" />
            <InstancesEmptyState onCreate={openCreateModal} />
          </Stack>
        </Container>
      );
    }

    const running = generators.filter(
      (instance) => instance.status.is_running
    ).length;

    // Row ids are the instance ids (via getRowId in the table), so the
    // selection keys are ids directly - filter out any that no longer exist.
    const existingIds = new Set(generators.map((instance) => instance.id));
    const selectedInstanceIds = Object.keys(rowSelection).filter((id) =>
      existingIds.has(id)
    );
    const hasSelection = selectedInstanceIds.length > 0;

    return (
      <Container size="100%">
        <Stack>
          <Group align="baseline" gap="sm">
            <PageTitle title="Instances" />
            <Text size="sm" c="dimmed">
              {total} {total === 1 ? 'instance' : 'instances'} · {running}{' '}
              active
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
                      onClick={() => setParams({ instance: null })}
                      data-input-section
                    >
                      <IconX size={16} />
                    </ActionIcon>
                  }
                  placeholder="search by instance..."
                  value={instanceFilter}
                  onChange={(event) =>
                    setParams({ instance: event.target.value || null })
                  }
                />
                <TextInput
                  leftSection={<IconSearch size={16} />}
                  rightSection={
                    <ActionIcon
                      variant="transparent"
                      onClick={() => setParams({ project: null })}
                      data-input-section
                    >
                      <IconX size={16} />
                    </ActionIcon>
                  }
                  placeholder="search by project..."
                  value={projectNameFilter}
                  onChange={(event) =>
                    setParams({ project: event.target.value || null })
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
                    // The URL keeps `inactive`, so filtered links stay valid.
                    { label: 'Idle', value: 'inactive' },
                  ]}
                />
              </Group>
              <Group gap="sm">
                {hasSelection && (
                  <Text size="sm" c="dimmed">
                    {selectedInstanceIds.length} selected
                  </Text>
                )}
                <ActionIcon.Group>
                  <ActionIcon
                    size="lg"
                    variant="default"
                    title="Start selected"
                    disabled={!hasSelection}
                    loading={bulkStart.isPending}
                    onClick={() => handleBulkStart(selectedInstanceIds)}
                  >
                    <IconPlayerPlay size={18} />
                  </ActionIcon>
                  <ActionIcon
                    size="lg"
                    variant="default"
                    title="Stop selected"
                    disabled={!hasSelection}
                    loading={bulkStop.isPending}
                    onClick={() => handleBulkStop(selectedInstanceIds)}
                  >
                    <IconPlayerStop size={18} />
                  </ActionIcon>
                  <ActionIcon
                    size="lg"
                    variant="default"
                    title="Delete selected"
                    disabled={!hasSelection}
                    loading={bulkDelete.isPending}
                    onClick={() =>
                      modals.openConfirmModal({
                        title: CONFIRM.deleteInstances.title,
                        children: (
                          <Text size="sm">
                            {CONFIRM.deleteInstances.body(
                              selectedInstanceIds.join(', ')
                            )}
                          </Text>
                        ),
                        labels: {
                          cancel: CONFIRM.deleteInstances.cancel,
                          confirm: CONFIRM.deleteInstances.confirm,
                        },
                        onConfirm: () => handleBulkDelete(selectedInstanceIds),
                      })
                    }
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
                    void refetchStats();
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

          <InstancesTable
            data={generators}
            projectNameFilter={projectNameFilter}
            instancesFilter={instanceFilter}
            statusMode={statusMode}
            statsById={statsById}
            rowSelection={rowSelection}
            onRowSelectionChange={setRowSelection}
          />
        </Stack>
      </Container>
    );
  }

  return <></>;
}
