import { useMutation, useQueries, useQuery, useQueryClient } from '@tanstack/react-query';

import {
  addGeneratorToScenario,
  clearScenarioGlobalState,
  deleteScenario,
  deleteScenarioGlobalStateKey,
  getGlobalsUsage,
  getScenarioGlobalState,
  listScenarios,
  removeGeneratorFromScenario,
  updateScenarioGlobalState,
} from '../routes/scenarios';

const SCENARIOS_QUERY_KEY = ['scenarios'];

export function useScenarios() {
  return useQuery({
    queryKey: SCENARIOS_QUERY_KEY,
    queryFn: listScenarios,
  });
}

export function useDeleteScenarioMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (name: string) => deleteScenario(name),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: SCENARIOS_QUERY_KEY,
      });
      await queryClient.invalidateQueries({
        queryKey: ['startup'],
      });
    },
  });
}

export function useAddGeneratorToScenarioMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ name, generatorId }: { name: string; generatorId: string }) =>
      addGeneratorToScenario(name, generatorId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: SCENARIOS_QUERY_KEY,
      });
      await queryClient.invalidateQueries({
        queryKey: ['startup'],
      });
    },
  });
}

export function useRemoveGeneratorFromScenarioMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ name, generatorId }: { name: string; generatorId: string }) =>
      removeGeneratorFromScenario(name, generatorId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: SCENARIOS_QUERY_KEY,
      });
      await queryClient.invalidateQueries({
        queryKey: ['startup'],
      });
    },
  });
}

export function useGlobalsUsage(scenarioName: string, generatorName: string) {
  return useQuery({
    queryKey: ['globals-usage', scenarioName, generatorName],
    queryFn: () => getGlobalsUsage(scenarioName, generatorName),
    staleTime: 60_000,
  });
}

export function useMultiGlobalsUsage(
  scenarioName: string,
  generatorNames: string[]
) {
  return useQueries({
    queries: generatorNames.map((name) => ({
      queryKey: ['globals-usage', scenarioName, name],
      queryFn: () => getGlobalsUsage(scenarioName, name),
      staleTime: 60_000,
    })),
  });
}

const SCENARIO_GLOBAL_STATE_KEY = (name: string) => [
  ...SCENARIOS_QUERY_KEY,
  name,
  'global-state',
];

export function useScenarioGlobalState(
  name: string,
  options?: { refetchInterval?: number | false }
) {
  return useQuery({
    queryKey: SCENARIO_GLOBAL_STATE_KEY(name),
    queryFn: () => getScenarioGlobalState(name),
    refetchInterval: options?.refetchInterval ?? false,
  });
}

export function useUpdateScenarioGlobalStateMutation(name: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (state: Record<string, unknown>) =>
      updateScenarioGlobalState(name, state),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: SCENARIO_GLOBAL_STATE_KEY(name),
      });
    },
  });
}

export function useClearScenarioGlobalStateMutation(name: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => clearScenarioGlobalState(name),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: SCENARIO_GLOBAL_STATE_KEY(name),
      });
    },
  });
}

export function useDeleteScenarioGlobalStateKeyMutation(name: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (key: string) => deleteScenarioGlobalStateKey(name, key),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: SCENARIO_GLOBAL_STATE_KEY(name),
      });
    },
  });
}
