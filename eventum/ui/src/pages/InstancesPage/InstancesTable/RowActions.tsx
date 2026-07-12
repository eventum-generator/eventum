import { Menu, Text } from '@mantine/core';
import { modals } from '@mantine/modals';
import { notifications } from '@mantine/notifications';
import {
  IconCopy,
  IconEdit,
  IconGauge,
  IconLogs,
  IconPlayerPlay,
  IconPlayerStop,
  IconTrash,
} from '@tabler/icons-react';
import { FC, ReactNode } from 'react';
import { Link } from 'react-router-dom';

import { CloneInstanceModal } from '../CloneInstanceModal';
import { MetricsModal } from './MetricsModal';
import {
  useDeleteGeneratorMutation,
  useStartGeneratorMutation,
  useStopGeneratorMutation,
  useUpdateGeneratorStatus,
} from '@/api/hooks/useGenerators';
import { useDeleteGeneratorFromStartupMutation } from '@/api/hooks/useStartup';
import { streamGeneratorLogs } from '@/api/routes/generators';
import { GeneratorStatus } from '@/api/routes/generators/schemas';
import { LogsModal } from '@/components/modals/LogsModal';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';
import { ROUTE_PATHS } from '@/routing/paths';

interface RowActionsProps {
  target: ReactNode;
  instanceId: string;
  instanceStatus: GeneratorStatus;
  existingInstanceIds: string[];
}

export const RowActions: FC<RowActionsProps> = ({
  target,
  instanceId,
  instanceStatus,
  existingInstanceIds,
}) => {
  const startGenerator = useStartGeneratorMutation();
  const stopGenerator = useStopGeneratorMutation();
  const deleteGenerator = useDeleteGeneratorMutation();
  const deleteGeneratorFromStartup = useDeleteGeneratorFromStartupMutation();
  const updateGeneratorStatus = useUpdateGeneratorStatus();

  function handleClone() {
    modals.open({
      title: 'Clone instance',
      children: (
        <CloneInstanceModal
          sourceInstanceId={instanceId}
          existingInstanceIds={existingInstanceIds}
        />
      ),
      size: 'lg',
    });
  }

  function handleShowMetrics() {
    modals.open({
      title: `Instance metrics`,
      children: <MetricsModal instanceId={instanceId} />,
      size: '70vw',
    });
  }

  function handleShowLogs() {
    modals.open({
      title: `Instance logs`,
      children: (
        <LogsModal
          getWebSocket={() => streamGeneratorLogs(instanceId, 10_048_576)}
        />
      ),
      size: '80vw',
    });
  }

  function handleStart() {
    updateGeneratorStatus.mutate({
      id: instanceId,
      status: {
        is_initializing: true,
        is_running: false,
        is_ended_up: false,
        is_ended_up_successfully: false,
        is_stopping: false,
      },
    });

    startGenerator.mutate(
      { id: instanceId },
      {
        onSuccess: () => {
          notifications.show({
            title: 'Success',
            message: 'Instance is started',
            color: 'green',
          });
        },
        onError: (error) => {
          notifications.show({
            title: 'Error',
            message: (
              <>
                Failed to start instance
                <ShowErrorDetailsAnchor error={error} prependDot />
              </>
            ),
            color: 'red',
          });
        },
      }
    );
  }

  function handleStop() {
    updateGeneratorStatus.mutate({
      id: instanceId,
      status: {
        is_initializing: false,
        is_running: false,
        is_ended_up: false,
        is_ended_up_successfully: false,
        is_stopping: true,
      },
    });

    stopGenerator.mutate(
      { id: instanceId },
      {
        onSuccess: () => {
          notifications.show({
            title: 'Success',
            message: 'Instance is stopped',
            color: 'green',
          });
        },
        onError: (error) => {
          notifications.show({
            title: 'Error',
            message: (
              <>
                Failed to stop instance
                <ShowErrorDetailsAnchor error={error} prependDot />
              </>
            ),
            color: 'red',
          });
        },
      }
    );
  }

  function handleDelete() {
    deleteGenerator.mutate(
      { id: instanceId },
      {
        onSuccess: () => {
          deleteGeneratorFromStartup.mutate(
            { id: instanceId },
            {
              onSuccess: () => {
                notifications.show({
                  title: 'Success',
                  message: 'Instance is deleted',
                  color: 'green',
                });
              },
              onError: (error) => {
                notifications.show({
                  title: 'Error',
                  message: (
                    <>
                      Failed to delete instance definition from startup
                      <ShowErrorDetailsAnchor error={error} prependDot />
                    </>
                  ),
                  color: 'red',
                });
              },
            }
          );
        },
        onError: (error) => {
          notifications.show({
            title: 'Error',
            message: (
              <>
                Failed to delete instance
                <ShowErrorDetailsAnchor error={error} prependDot />
              </>
            ),
            color: 'red',
          });
        },
      }
    );
  }

  return (
    <Menu shadow="md" width={170}>
      <Menu.Target>{target}</Menu.Target>

      <Menu.Dropdown>
        <Menu.Item
          component={Link}
          to={`${ROUTE_PATHS.INSTANCES}/${instanceId}`}
          leftSection={<IconEdit size={14} />}
        >
          Edit
        </Menu.Item>
        <Menu.Item leftSection={<IconCopy size={14} />} onClick={handleClone}>
          Clone
        </Menu.Item>

        <Menu.Divider />

        <Menu.Item
          leftSection={<IconGauge size={14} />}
          onClick={handleShowMetrics}
          disabled={!instanceStatus.is_running}
        >
          Show metrics
        </Menu.Item>
        <Menu.Item
          leftSection={<IconLogs size={14} />}
          onClick={handleShowLogs}
        >
          Show logs
        </Menu.Item>

        <Menu.Divider />

        <Menu.Item
          leftSection={<IconPlayerPlay size={14} />}
          onClick={handleStart}
          disabled={
            instanceStatus.is_initializing ||
            instanceStatus.is_running ||
            instanceStatus.is_stopping
          }
        >
          Start
        </Menu.Item>
        <Menu.Item
          leftSection={<IconPlayerStop size={14} />}
          onClick={handleStop}
          disabled={!instanceStatus.is_running}
        >
          Stop
        </Menu.Item>

        <Menu.Divider />

        <Menu.Item
          color="red"
          leftSection={<IconTrash size={14} />}
          onClick={() =>
            modals.openConfirmModal({
              title: 'Deleting instance',
              children: (
                <Text size="sm">
                  Instance <b>{instanceId}</b> will be deleted. Do you want to
                  continue?
                </Text>
              ),
              labels: { cancel: 'Cancel', confirm: 'Confirm' },
              onConfirm: handleDelete,
            })
          }
          disabled={
            instanceStatus.is_running ||
            instanceStatus.is_initializing ||
            instanceStatus.is_stopping
          }
        >
          Delete
        </Menu.Item>
      </Menu.Dropdown>
    </Menu>
  );
};
