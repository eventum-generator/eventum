import {
  ActionIcon,
  Alert,
  Box,
  Button,
  Center,
  Checkbox,
  Container,
  Group,
  Loader,
  Paper,
  Stack,
  Text,
  TextInput,
} from '@mantine/core';
import { modals } from '@mantine/modals';
import { notifications } from '@mantine/notifications';
import {
  IconAlertSquareRounded,
  IconPlayerPlay,
  IconPlayerStop,
  IconRefresh,
  IconSearch,
  IconTrash,
  IconX,
} from '@tabler/icons-react';
import { RowSelectionState } from '@tanstack/react-table';
import { useState } from 'react';

import { CreateInstanceModal } from './CreateInstanceModal';
import { InstancesTable } from './InstancesTable';
import {
  useBulkDeleteGeneratorMutation,
  useBulkStartGeneratorMutation,
  useBulkStopGeneratorMutation,
  useGenerators,
  useUpdateGeneratorStatus,
} from '@/api/hooks/useGenerators';
import { useBulkDeleteGeneratorsFromStartupMutation } from '@/api/hooks/useStartup';
import { PageTitle } from '@/components/ui/PageTitle';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';

export default function InstancesPage() {
  const [instanceFilter, setInstanceFilter] = useState('');
  const [projectNameFilter, setProjectNameFilter] = useState('');
  const [runningOnlyFilter, setRunningOnlyFilter] = useState(false);
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({});

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
          icon={<Box c="red" component={IconAlertSquareRounded}></Box>}
          title="Failed to load instances list"
        >
          {generatorsError.message}
          <ShowErrorDetailsAnchor error={generatorsError} prependDot />
        </Alert>
      </Container>
    );
  }

  if (isGeneratorsSuccess) {
    const selectedInstanceIds = Object.keys(rowSelection)
      .map((rowId) => generators[Number(rowId)]?.id)
      .filter((id) => id !== undefined);

    return (
      <Container size="100%">
        <Stack>
          <PageTitle title="Instances" />
          <Paper withBorder p="sm">
            <Group justify="space-between" align="center">
              <Group>
                <TextInput
                  leftSection={<IconSearch size={16} />}
                  rightSection={
                    <ActionIcon
                      variant="transparent"
                      onClick={() => setInstanceFilter('')}
                      data-input-section
                    >
                      <IconX size={16} />
                    </ActionIcon>
                  }
                  placeholder="search by instance..."
                  value={instanceFilter}
                  onChange={(event) => setInstanceFilter(event.target.value)}
                />
                <TextInput
                  leftSection={<IconSearch size={16} />}
                  rightSection={
                    <ActionIcon
                      variant="transparent"
                      onClick={() => setProjectNameFilter('')}
                      data-input-section
                    >
                      <IconX size={16} />
                    </ActionIcon>
                  }
                  placeholder="search by project..."
                  value={projectNameFilter}
                  onChange={(event) => setProjectNameFilter(event.target.value)}
                />
                <Checkbox
                  label="Running only"
                  checked={runningOnlyFilter}
                  onChange={(event) =>
                    setRunningOnlyFilter(event.currentTarget.checked)
                  }
                />
              </Group>
              <Group gap="xs">
                <Group gap={0}>
                  <ActionIcon
                    size="lg"
                    variant="default"
                    title="Delete"
                    style={{
                      borderTopRightRadius: 0,
                      borderBottomRightRadius: 0,
                    }}
                    onClick={() =>
                      modals.openConfirmModal({
                        title: 'Deleting instances',
                        children: (
                          <Text size="sm">
                            Instance(s) <b>{selectedInstanceIds.join(', ')}</b>{' '}
                            will be deleted. Do you want to continue?
                          </Text>
                        ),
                        labels: { cancel: 'Cancel', confirm: 'Confirm' },
                        onConfirm: () => handleBulkDelete(selectedInstanceIds),
                      })
                    }
                    loading={bulkDelete.isPending}
                    disabled={selectedInstanceIds.length === 0}
                  >
                    <Box
                      c={selectedInstanceIds.length === 0 ? undefined : 'red'}
                    >
                      <IconTrash size={20} />
                    </Box>
                  </ActionIcon>
                  <ActionIcon
                    size="lg"
                    variant="default"
                    title="Refresh"
                    bdrs={0}
                    onClick={() => void refetchGenerators()}
                    loading={isGeneratorsLoading}
                  >
                    <IconRefresh size={20} />
                  </ActionIcon>
                  <ActionIcon
                    size="lg"
                    variant="default"
                    title="Stop selected"
                    bdrs={0}
                    disabled={selectedInstanceIds.length === 0}
                    loading={bulkStop.isPending}
                    onClick={() => handleBulkStop(selectedInstanceIds)}
                  >
                    <IconPlayerStop size={20} />
                  </ActionIcon>
                  <ActionIcon
                    size="lg"
                    variant="default"
                    title="Start selected"
                    style={{
                      borderTopLeftRadius: 0,
                      borderBottomLeftRadius: 0,
                    }}
                    disabled={selectedInstanceIds.length === 0}
                    loading={bulkStart.isPending}
                    onClick={() => handleBulkStart(selectedInstanceIds)}
                  >
                    <IconPlayerPlay size={20} />
                  </ActionIcon>
                </Group>
                <Button
                  onClick={() =>
                    modals.open({
                      title: 'New instance',
                      children: (
                        <CreateInstanceModal
                          existingInstanceIds={generators.map(
                            (instance) => instance.id
                          )}
                        />
                      ),
                      size: 'lg',
                    })
                  }
                >
                  Create new
                </Button>
              </Group>
            </Group>
          </Paper>

          <InstancesTable
            data={generators}
            projectNameFilter={projectNameFilter}
            instancesFilter={instanceFilter}
            runningOnlyFilter={runningOnlyFilter}
            rowSelection={rowSelection}
            onRowSelectionChange={setRowSelection}
          />
        </Stack>
      </Container>
    );
  }

  return <></>;
}
