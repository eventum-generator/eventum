import { Paper } from '@mantine/core';
import { IconDatabase } from '@tabler/icons-react';
import { FC, useCallback } from 'react';

import {
  useClearScenarioGlobalStateMutation,
  useDeleteScenarioGlobalStateKeyMutation,
  useScenarioGlobalState,
  useUpdateScenarioGlobalStateMutation,
} from '@/api/hooks/useScenarios';
import { KeyValueTable } from '@/components/state';
import {
  showErrorNotification,
  showSuccessNotification,
} from '@/utils/notifications';

interface GlobalStatePanelProps {
  scenarioName: string;
}

export const GlobalStatePanel: FC<GlobalStatePanelProps> = ({ scenarioName }) => {
  const { data, isLoading, isError, error, isSuccess, refetch } =
    useScenarioGlobalState(scenarioName, { refetchInterval: 5000 });
  const updateState = useUpdateScenarioGlobalStateMutation(scenarioName);
  const deleteKey = useDeleteScenarioGlobalStateKeyMutation(scenarioName);
  const clearState = useClearScenarioGlobalStateMutation(scenarioName);

  const handleUpdateKey = useCallback(
    (key: string, value: unknown) => {
      updateState.mutate(
        { [key]: value },
        {
          onSuccess: () => {
            showSuccessNotification('Updated', `Key "${key}" updated`);
          },
          onError: (updateError) => {
            showErrorNotification('Failed to update key', updateError);
          },
        },
      );
    },
    [updateState],
  );

  const handleDeleteKey = useCallback(
    (key: string) => {
      deleteKey.mutate(key, {
        onSuccess: () => {
          showSuccessNotification('Deleted', `Key "${key}" removed`);
        },
        onError: (deleteError) => {
          showErrorNotification('Failed to delete key', deleteError);
        },
      });
    },
    [deleteKey],
  );

  const handleAddKey = useCallback(
    (key: string, value: unknown) => {
      updateState.mutate(
        { [key]: value },
        {
          onSuccess: () => {
            showSuccessNotification('Added', `Key "${key}" added`);
          },
          onError: (addError) => {
            showErrorNotification('Failed to add key', addError);
          },
        },
      );
    },
    [updateState],
  );

  const handleClear = useCallback(() => {
    clearState.mutate(undefined, {
      onSuccess: () => {
        showSuccessNotification('Cleared', 'Global state cleared');
      },
      onError: (clearError) => {
        showErrorNotification('Failed to clear global state', clearError);
      },
    });
  }, [clearState]);

  return (
    <Paper withBorder p="md" h="100%">
      <KeyValueTable
        data={data}
        isLoading={isLoading}
        isError={isError}
        error={error}
        isSuccess={isSuccess}
        onRefetch={() => void refetch()}
        onUpdateKey={handleUpdateKey}
        onDeleteKey={handleDeleteKey}
        onAddKey={handleAddKey}
        onClear={handleClear}
        title="Global State"
        titleIcon={<IconDatabase size={16} />}
        titleOrder={5}
        isClearPending={clearState.isPending}
        emptyMessage="Global state is empty"
        warningTitle="Global state"
        warningMessage="Updating global state will affect all currently running generator instances."
      />
    </Paper>
  );
};
