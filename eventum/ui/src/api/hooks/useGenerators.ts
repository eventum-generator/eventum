import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import {
  addGenerator,
  bulkRemoveGenerators as bulkDeleteGenerators,
  bulkStartGenerators,
  bulkStopGenerators,
  deleteGenerator,
  getGenerator,
  getGeneratorStats,
  getGeneratorStatus,
  getRunningGeneratorsStats,
  listGenerators,
  startGenerator,
  stopGenerator,
  updateGenerator,
} from '../routes/generators';
import {
  GeneratorParameters,
  GeneratorStatus,
  GeneratorsInfo,
} from '../routes/generators/schemas';

const GENERATORS_QUERY_KEY = ['generators'];

export function useGenerators() {
  return useQuery({
    queryKey: GENERATORS_QUERY_KEY,
    queryFn: listGenerators,
    structuralSharing: false,
  });
}

export function useGenerator(id: string) {
  return useQuery({
    queryKey: [...GENERATORS_QUERY_KEY, id],
    queryFn: () => getGenerator(id),
  });
}

export function useAddGeneratorMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, params }: { id: string; params: GeneratorParameters }) =>
      addGenerator(id, params),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: GENERATORS_QUERY_KEY,
        exact: true,
      });
    },
  });
}

export function useUpdateGeneratorMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, params }: { id: string; params: GeneratorParameters }) =>
      updateGenerator(id, params),
    onSuccess: async (_, { id }) => {
      await queryClient.invalidateQueries({
        queryKey: [...GENERATORS_QUERY_KEY, id],
        exact: true,
      });
    },
  });
}

export function useDeleteGeneratorMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id }: { id: string }) => deleteGenerator(id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: GENERATORS_QUERY_KEY,
        exact: true,
      });
    },
  });
}

export function useGeneratorStatus(id: string) {
  return useQuery({
    queryKey: [...GENERATORS_QUERY_KEY, id, 'status'],
    queryFn: () => getGeneratorStatus(id),
  });
}

export function useGeneratorStats(id: string) {
  return useQuery({
    queryKey: [...GENERATORS_QUERY_KEY, id, 'stats'],
    queryFn: () => getGeneratorStats(id),
  });
}

export function useRunningGeneratorsStats() {
  return useQuery({
    queryKey: [...GENERATORS_QUERY_KEY, 'group-actions', 'stats-running'],
    queryFn: getRunningGeneratorsStats,
  });
}

export function useStartGeneratorMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id }: { id: string }) => startGenerator(id),
    onSuccess: async (_, { id }) => {
      await queryClient.invalidateQueries({
        queryKey: [...GENERATORS_QUERY_KEY, id],
        exact: false,
      });
      await queryClient.invalidateQueries({
        queryKey: GENERATORS_QUERY_KEY,
        exact: true,
      });
    },
  });
}

export function useStopGeneratorMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id }: { id: string }) => stopGenerator(id),
    onSuccess: async (_, { id }) => {
      await queryClient.invalidateQueries({
        queryKey: [...GENERATORS_QUERY_KEY, id],
        exact: false,
      });
      await queryClient.invalidateQueries({
        queryKey: GENERATORS_QUERY_KEY,
        exact: true,
      });
    },
  });
}

export function useBulkStartGeneratorMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ ids }: { ids: string[] }) => bulkStartGenerators(ids),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: GENERATORS_QUERY_KEY,
        exact: false,
      });
    },
  });
}

export function useBulkStopGeneratorMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ ids }: { ids: string[] }) => bulkStopGenerators(ids),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: GENERATORS_QUERY_KEY,
        exact: false,
      });
    },
  });
}

export function useBulkDeleteGeneratorMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ ids }: { ids: string[] }) => bulkDeleteGenerators(ids),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: GENERATORS_QUERY_KEY,
        exact: false,
      });
    },
  });
}

export function useUpdateGeneratorStatus() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      id,
      status,
    }: {
      id: string;
      status: GeneratorStatus;
    }) => {
      await queryClient.setQueryData(
        GENERATORS_QUERY_KEY,
        (oldValue: GeneratorsInfo) =>
          oldValue.map((item) => (item.id === id ? { ...item, status } : item))
      );
    },
  });
}
