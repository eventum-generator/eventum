import { useCallback } from 'react';

import {
  useBulkStartGeneratorMutation,
  useBulkStopGeneratorMutation,
} from '@/api/hooks/useGenerators';

export function useScenarioBulkActions(generatorIds: string[]) {
  const bulkStart = useBulkStartGeneratorMutation();
  const bulkStop = useBulkStopGeneratorMutation();

  const startAll = useCallback(() => {
    bulkStart.mutate({ ids: generatorIds });
  }, [bulkStart, generatorIds]);

  const stopAll = useCallback(() => {
    bulkStop.mutate({ ids: generatorIds });
  }, [bulkStop, generatorIds]);

  return {
    startAll,
    stopAll,
    isStarting: bulkStart.isPending,
    isStopping: bulkStop.isPending,
    bulkStart,
    bulkStop,
  };
}
