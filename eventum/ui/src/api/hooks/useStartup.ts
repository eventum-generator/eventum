import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import {
  addGeneratorToStartup,
  bulkDeleteGeneratorsFromStartup,
  deleteGeneratorFromStartup,
  getStartupGenerator,
  getStartupGenerators,
  updateGeneratorInStartup,
} from '../routes/startup';
import { StartupGeneratorParameters } from '../routes/startup/schemas';

const STARTUP_QUERY_KEY = ['startup'];

export function useStartupGenerators() {
  return useQuery({
    queryKey: STARTUP_QUERY_KEY,
    queryFn: getStartupGenerators,
  });
}

export function useStartupGenerator(id: string) {
  return useQuery({
    queryKey: [...STARTUP_QUERY_KEY, id],
    queryFn: () => getStartupGenerator(id),
  });
}

export function useAddGeneratorToStartupMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      id,
      params,
    }: {
      id: string;
      params: StartupGeneratorParameters;
    }) => addGeneratorToStartup(id, params),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: STARTUP_QUERY_KEY,
        exact: true,
      });
    },
  });
}

export function useUpdateGeneratorInStartupMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      id,
      params,
    }: {
      id: string;
      params: StartupGeneratorParameters;
    }) => updateGeneratorInStartup(id, params),
    onSuccess: async (_, { id }) => {
      await queryClient.invalidateQueries({
        queryKey: [...STARTUP_QUERY_KEY, id],
        exact: true,
      });
    },
  });
}

export function useDeleteGeneratorFromStartupMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id }: { id: string }) => deleteGeneratorFromStartup(id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: STARTUP_QUERY_KEY,
        exact: true,
      });
    },
  });
}

export function useBulkDeleteGeneratorsFromStartupMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ ids }: { ids: string[] }) =>
      bulkDeleteGeneratorsFromStartup(ids),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: STARTUP_QUERY_KEY,
        exact: true,
      });
    },
  });
}
