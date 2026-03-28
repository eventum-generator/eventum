import { Menu, Text } from '@mantine/core';
import { modals } from '@mantine/modals';
import {
  IconEdit,
  IconPlayerPlay,
  IconPlayerStop,
  IconTrash,
} from '@tabler/icons-react';
import { FC, ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';

import {
  useBulkStartGeneratorMutation,
  useBulkStopGeneratorMutation,
  useUpdateGeneratorStatus,
} from '@/api/hooks/useGenerators';
import { useDeleteScenarioMutation } from '@/api/hooks/useScenarios';
import { ROUTE_PATHS } from '@/routing/paths';
import {
  showErrorNotification,
  showSuccessNotification,
} from '@/utils/notifications';

interface RowActionsProps {
  target: ReactNode;
  scenarioName: string;
  generatorIds: string[];
  hasRunning: boolean;
  hasInactive: boolean;
}

export const RowActions: FC<RowActionsProps> = ({
  target,
  scenarioName,
  generatorIds,
  hasRunning,
  hasInactive,
}) => {
  const navigate = useNavigate();
  const deleteScenario = useDeleteScenarioMutation();
  const bulkStart = useBulkStartGeneratorMutation();
  const bulkStop = useBulkStopGeneratorMutation();
  const updateStatus = useUpdateGeneratorStatus();

  function handleEdit() {
    void navigate(
      `${ROUTE_PATHS.SCENARIOS}/${encodeURIComponent(scenarioName)}`,
    );
  }

  function handleStart() {
    for (const id of generatorIds) {
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
      { ids: generatorIds },
      {
        onSuccess: () =>
          showSuccessNotification('Success', `Scenario "${scenarioName}" started`),
        onError: (e) =>
          showErrorNotification('Failed to start scenario', e),
      },
    );
  }

  function handleStop() {
    for (const id of generatorIds) {
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
      { ids: generatorIds },
      {
        onSuccess: () =>
          showSuccessNotification('Success', `Scenario "${scenarioName}" stopped`),
        onError: (e) =>
          showErrorNotification('Failed to stop scenario', e),
      },
    );
  }

  function handleDelete() {
    modals.openConfirmModal({
      title: 'Delete scenario',
      children: (
        <Text size="sm">
          Delete scenario <b>{scenarioName}</b>? Generators will not be
          deleted.
        </Text>
      ),
      labels: { cancel: 'Cancel', confirm: 'Delete' },
      onConfirm: () => {
        deleteScenario.mutate(
          scenarioName,
          {
            onSuccess: () =>
              showSuccessNotification(
                'Deleted',
                `Scenario "${scenarioName}" deleted`,
              ),
            onError: (deleteError) =>
              showErrorNotification('Failed to delete scenario', deleteError),
          },
        );
      },
    });
  }

  return (
    <Menu shadow="md" width={170}>
      <Menu.Target>{target}</Menu.Target>

      <Menu.Dropdown>
        <Menu.Item
          leftSection={<IconEdit size={14} />}
          onClick={handleEdit}
        >
          Edit
        </Menu.Item>

        <Menu.Item
          leftSection={<IconPlayerPlay size={14} />}
          onClick={handleStart}
          disabled={!hasInactive}
        >
          Start
        </Menu.Item>

        <Menu.Item
          leftSection={<IconPlayerStop size={14} />}
          onClick={handleStop}
          disabled={!hasRunning}
        >
          Stop
        </Menu.Item>

        <Menu.Divider />

        <Menu.Item
          color="red"
          leftSection={<IconTrash size={14} />}
          onClick={handleDelete}
        >
          Delete
        </Menu.Item>
      </Menu.Dropdown>
    </Menu>
  );
};
