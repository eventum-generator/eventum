import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import {
  addRepository,
  checkRepository,
  deleteRepository,
  getCatalog,
  getRepositories,
  installGenerator,
  refreshCatalog,
} from '@/api/routes/repositories';
import { Repository } from '@/api/routes/repositories/schemas';

const REPOSITORIES_QUERY_KEY = ['repositories'];
const CATALOG_QUERY_KEY = ['repository-catalog'];

// Installing writes a project directory, so the lists of projects the
// workspace shows are no longer current.
const GENERATOR_CONFIG_DIRS_QUERY_KEYS = [
  ['generator-config-dirs'],
  ['generator-config-dirs-extended'],
];

export function useRepositories() {
  return useQuery({
    queryKey: REPOSITORIES_QUERY_KEY,
    queryFn: getRepositories,
  });
}

export function useRepositoryCatalog(name: string, enabled: boolean) {
  return useQuery({
    queryKey: [...CATALOG_QUERY_KEY, name],
    queryFn: () => getCatalog(name),
    enabled,
    // The catalog is read from a remote on request; a refetch on every
    // focus would reach out to it again.
    staleTime: Infinity,
    retry: false,
  });
}

export function useAddRepositoryMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      repository,
      verify,
    }: {
      repository: Repository;
      verify: boolean;
    }) => addRepository(repository, verify),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: REPOSITORIES_QUERY_KEY,
        exact: true,
      });
    },
  });
}

export function useDeleteRepositoryMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (name: string) => deleteRepository(name),
    onSuccess: async (_, name) => {
      queryClient.removeQueries({ queryKey: [...CATALOG_QUERY_KEY, name] });
      await queryClient.invalidateQueries({
        queryKey: REPOSITORIES_QUERY_KEY,
        exact: true,
      });
    },
  });
}

export function useCheckRepositoryMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (name: string) => checkRepository(name),
    onSettled: async () => {
      await queryClient.invalidateQueries({
        queryKey: REPOSITORIES_QUERY_KEY,
        exact: true,
      });
    },
  });
}

export function useRefreshCatalogMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (name: string) => refreshCatalog(name),
    onSuccess: (catalog, name) => {
      queryClient.setQueryData([...CATALOG_QUERY_KEY, name], catalog);
    },
  });
}

export function useInstallGeneratorMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      name,
      entry,
      projectName,
    }: {
      name: string;
      entry: string;
      projectName: string;
    }) => installGenerator(name, entry, projectName),
    onSuccess: async (_, { name }) => {
      // The catalog names what of it is installed, so it is read
      // again - from what was already fetched, without reaching the
      // repository.
      await queryClient.invalidateQueries({
        queryKey: [...CATALOG_QUERY_KEY, name],
      });

      await Promise.all(
        GENERATOR_CONFIG_DIRS_QUERY_KEYS.map((key) =>
          queryClient.invalidateQueries({ queryKey: key, exact: true })
        )
      );
    },
  });
}
