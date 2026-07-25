import { List, Menu, Text } from '@mantine/core';
import { modals } from '@mantine/modals';
import {
  IconCursorText,
  IconEdit,
  IconPlayerPlay,
  IconPlayerStop,
  IconTrash,
} from '@tabler/icons-react';
import { FC, ReactNode } from 'react';
import { Link } from 'react-router-dom';

import { RenameScenarioModal } from '../RenameScenarioModal';
import {
  useBulkStartGeneratorMutation,
  useBulkStopGeneratorMutation,
  useUpdateGeneratorStatus,
} from '@/api/hooks/useGenerators';
import { useDeleteScenarioMutation } from '@/api/hooks/useScenarios';
import { useStartupGenerators } from '@/api/hooks/useStartup';
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
  getAffectedScenarios: (
    scenarioName: string,
    generatorIds: string[]
  ) => string[];
}

export const RowActions: FC<RowActionsProps> = ({
  target,
  scenarioName,
  generatorIds,
  hasRunning,
  hasInactive,
  getAffectedScenarios,
}) => {
  const deleteScenario = useDeleteScenarioMutation();

  // Reads the query the page itself renders from, so no extra request.
  // Passing names down as a prop would rebuild the table columns on
  // every poll - see the note on getAffectedScenarios in the page.
  const { data: startupEntries } = useStartupGenerators();
  const bulkStart = useBulkStartGeneratorMutation();
  const bulkStop = useBulkStopGeneratorMutation();
  const updateStatus = useUpdateGeneratorStatus();

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
          showSuccessNotification(
            'Success',
            `Scenario "${scenarioName}" started`
          ),
        onError: (e) => showErrorNotification('Failed to start scenario', e),
      }
    );
  }

  function executeStop() {
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
          showSuccessNotification(
            'Success',
            `Scenario "${scenarioName}" stopped`
          ),
        onError: (e) => showErrorNotification('Failed to stop scenario', e),
      }
    );
  }

  function handleStop() {
    const affected = getAffectedScenarios(scenarioName, generatorIds);
    if (affected.length > 0) {
      modals.openConfirmModal({
        title: 'Shared instances detected',
        children: (
          <Text size="sm">
            Some instances in <b>{scenarioName}</b> are also used in other
            scenarios. Stopping them will affect:
            <List size="sm" mt="xs">
              {affected.map((name) => (
                <List.Item key={name}>
                  <b>{name}</b>
                </List.Item>
              ))}
            </List>
          </Text>
        ),
        labels: { cancel: 'Cancel', confirm: 'Stop anyway' },
        onConfirm: executeStop,
      });
    } else {
      executeStop();
    }
  }

  function handleRename() {
    modals.open({
      title: 'Rename scenario',
      children: (
        <RenameScenarioModal
          scenarioName={scenarioName}
          existingScenarioNames={[
            ...new Set(
              (startupEntries ?? []).flatMap((entry) => entry.scenarios ?? [])
            ),
          ]}
          instanceCount={generatorIds.length}
        />
      ),
    });
  }

  function handleDelete() {
    modals.openConfirmModal({
      title: 'Delete scenario',
      children: (
        <Text size="sm">
          Delete scenario <b>{scenarioName}</b>? Generators will not be deleted.
        </Text>
      ),
      labels: { cancel: 'Cancel', confirm: 'Delete' },
      onConfirm: () => {
        deleteScenario.mutate(scenarioName, {
          onSuccess: () =>
            showSuccessNotification(
              'Deleted',
              `Scenario "${scenarioName}" deleted`
            ),
          onError: (deleteError) =>
            showErrorNotification('Failed to delete scenario', deleteError),
        });
      },
    });
  }

  return (
    <Menu shadow="md" width={170}>
      <Menu.Target>{target}</Menu.Target>

      <Menu.Dropdown>
        <Menu.Item
          component={Link}
          to={`${ROUTE_PATHS.SCENARIOS}/${encodeURIComponent(scenarioName)}`}
          leftSection={<IconEdit size={14} />}
        >
          Edit
        </Menu.Item>

        <Menu.Item
          leftSection={<IconCursorText size={14} />}
          onClick={handleRename}
        >
          Rename
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
          color="var(--mantine-color-red-text)"
          leftSection={<IconTrash size={14} />}
          onClick={handleDelete}
        >
          Delete
        </Menu.Item>
      </Menu.Dropdown>
    </Menu>
  );
};
