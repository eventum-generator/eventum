import { useQueryClient } from '@tanstack/react-query';

import {
  useStartGeneratorMutation,
  useStopGeneratorMutation,
} from '@/api/hooks/useGenerators';
import {
  GeneratorStatus,
  GeneratorsInfo,
} from '@/api/routes/generators/schemas';
import {
  showErrorNotification,
  showSuccessNotification,
} from '@/utils/notifications';

const INITIALIZING: GeneratorStatus = {
  is_initializing: true,
  is_running: false,
  is_ended_up: false,
  is_ended_up_successfully: false,
  is_stopping: false,
};

const STOPPING: GeneratorStatus = {
  is_initializing: false,
  is_running: false,
  is_ended_up: false,
  is_ended_up_successfully: false,
  is_stopping: true,
};

/**
 * Start / stop / restart handlers for one instance. Each optimistically
 * writes the transitional status into both the single-status query (read by
 * the instance page header) and the list query (read elsewhere) so the UI
 * reacts instantly; the mutations then invalidate and reconcile.
 */
export function useInstanceActions(instanceId: string) {
  const queryClient = useQueryClient();
  const startGenerator = useStartGeneratorMutation();
  const stopGenerator = useStopGeneratorMutation();

  function setOptimisticStatus(status: GeneratorStatus) {
    queryClient.setQueryData(['generators', instanceId, 'status'], status);
    queryClient.setQueryData(['generators'], (old?: GeneratorsInfo) =>
      old?.map((g) => (g.id === instanceId ? { ...g, status } : g))
    );
  }

  function handleStart() {
    setOptimisticStatus(INITIALIZING);
    startGenerator.mutate(
      { id: instanceId },
      {
        onSuccess: () =>
          showSuccessNotification('Success', 'Instance is started'),
        onError: (error) =>
          showErrorNotification('Failed to start instance', error),
      }
    );
  }

  function handleStop() {
    setOptimisticStatus(STOPPING);
    stopGenerator.mutate(
      { id: instanceId },
      {
        onSuccess: () =>
          showSuccessNotification('Success', 'Instance is stopped'),
        onError: (error) =>
          showErrorNotification('Failed to stop instance', error),
      }
    );
  }

  function handleRestart() {
    setOptimisticStatus(STOPPING);
    stopGenerator.mutate(
      { id: instanceId },
      {
        onSuccess: () => {
          setOptimisticStatus(INITIALIZING);
          startGenerator.mutate(
            { id: instanceId },
            {
              onSuccess: () =>
                showSuccessNotification('Success', 'Instance is restarted'),
              onError: (error) =>
                showErrorNotification('Failed to start instance', error),
            }
          );
        },
        onError: (error) =>
          showErrorNotification('Failed to stop instance', error),
      }
    );
  }

  return {
    handleStart,
    handleStop,
    handleRestart,
    isStarting: startGenerator.isPending,
    isStopping: stopGenerator.isPending,
  };
}
