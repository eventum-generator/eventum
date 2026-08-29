import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import {
  getInstanceInfo,
  getInstanceSettings,
  restartInstance,
  stopInstance,
  updateInstanceSettings,
} from '@/api/routes/instance';
import { Settings } from '@/api/routes/instance/schemas';

const INSTANCE_SETTINGS_QUERY_KEY = ['instance', 'settings'];
const INSTANCE_INFO_QUERY_KEY = ['instance', 'info'];

export function useInstanceInfo(options?: {
  refetchInterval?: number | false;
}) {
  return useQuery({
    queryKey: INSTANCE_INFO_QUERY_KEY,
    queryFn: getInstanceInfo,
    refetchInterval: options?.refetchInterval,
  });
}

export function useInstanceSettings() {
  return useQuery({
    queryKey: INSTANCE_SETTINGS_QUERY_KEY,
    queryFn: getInstanceSettings,
  });
}

export function useUpdateInstanceSettingsMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ settings }: { settings: Settings }) =>
      updateInstanceSettings(settings),
    // The endpoint answers without a body, so what was written is only
    // known by reading it back - the instance normalises the settings
    // it stores and restarts on them.
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: INSTANCE_SETTINGS_QUERY_KEY,
      }),
  });
}

export function useStopInstanceMutation() {
  return useMutation({
    mutationFn: stopInstance,
  });
}

export function useRestartInstanceMutation() {
  return useMutation({
    mutationFn: restartInstance,
  });
}
