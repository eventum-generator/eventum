import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import {
  addRepository,
  checkRepository,
  deleteRepository,
  discoverRepositories,
  getCatalog,
  getRepositories,
  installGenerator,
  refreshCatalog,
} from '@/api/routes/repositories';
import { Repository } from '@/api/routes/repositories/schemas';

const REPOSITORIES_QUERY_KEY = ['repositories'];
const CATALOG_QUERY_KEY = ['repository-catalog'];
const DISCOVERY_QUERY_KEY = ['repository-discovery'];

// The instance holds what it read for ten minutes and answers from it,
// so asking again inside that window only repeats the same answer.
const DISCOVERY_STALE_TIME = 10 * 60 * 1000;

// Installing writes a project directory, so the lists of projects the
// workspace shows are no longer current.
const GENERATOR_CONFIG_DIRS_QUERY_KEYS = [
  ['generator-config-dirs'],
  ['generator-config-dirs-extended'],
];

// What a project of that name held before it was installed over must
// not be served for the one written now.
const PROJECT_QUERY_KEYS = [
  ['generator-config-dirs'],
  ['generator-config-dir-files'],
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

export function useDiscoveredRepositories(query: string, enabled: boolean) {
  return useQuery({
    queryKey: [...DISCOVERY_QUERY_KEY, query],
    queryFn: () => discoverRepositories(query),
    enabled,
    staleTime: DISCOVERY_STALE_TIME,
    // Searching is rate limited, so a failed search is reported rather
    // than repeated.
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
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: REPOSITORIES_QUERY_KEY,
          exact: true,
        }),
        // The published list marks what is already connected, and one
        // of them just became connected.
        queryClient.invalidateQueries({ queryKey: DISCOVERY_QUERY_KEY }),
      ]);
    },
  });
}

export function useDeleteRepositoryMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (name: string) => deleteRepository(name),
    onSuccess: async (_, name) => {
      queryClient.removeQueries({ queryKey: [...CATALOG_QUERY_KEY, name] });
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: REPOSITORIES_QUERY_KEY,
          exact: true,
        }),
        queryClient.invalidateQueries({ queryKey: DISCOVERY_QUERY_KEY }),
      ]);
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
    onSettled: async () => {
      // A fetch records what it found, so the state of the repository
      // is no longer what the list was showing.
      await queryClient.invalidateQueries({
        queryKey: REPOSITORIES_QUERY_KEY,
        exact: true,
      });
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
    onSuccess: async (_, { projectName }) => {
      // Any catalog of the same remote names the new project, not
      // only the one it was installed from, so every catalog is read
      // again - from what was already fetched, without reaching a
      // repository.
      await queryClient.invalidateQueries({ queryKey: CATALOG_QUERY_KEY });

      // A project of this name may have been in the workspace before;
      // nothing of it may be served for the one just written.
      for (const key of PROJECT_QUERY_KEYS) {
        queryClient.removeQueries({ queryKey: [...key, projectName] });
      }

      await Promise.all(
        GENERATOR_CONFIG_DIRS_QUERY_KEYS.map((key) =>
          queryClient.invalidateQueries({ queryKey: key, exact: true })
        )
      );
    },
  });
}
