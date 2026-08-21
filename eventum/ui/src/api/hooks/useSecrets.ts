import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import {
  deleteSecretValue,
  getSecretNames,
  getSecretReferences,
  getSecretValue,
  renameSecret,
  setSecretValue,
} from '@/api/routes/secrets';

const SECRETS_QUERY_KEY = ['secrets'];

// Renaming a secret repoints the repositories authenticating with
// it, so the list holding their old name is no longer current.
const REPOSITORIES_QUERY_KEY = ['repositories'];

export function useSecretReferences(name: string, enabled: boolean) {
  return useQuery({
    queryKey: [...SECRETS_QUERY_KEY, name, 'references'],
    queryFn: () => getSecretReferences(name),
    enabled,
  });
}

export function useRenameSecretMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ name, newName }: { name: string; newName: string }) =>
      renameSecret(name, newName),
    // On settled rather than on success: a rename that failed after
    // moving the keyring entry left both lists changed as well.
    onSettled: async () => {
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: SECRETS_QUERY_KEY,
          exact: true,
        }),
        queryClient.invalidateQueries({
          queryKey: REPOSITORIES_QUERY_KEY,
          exact: true,
        }),
      ]);
    },
  });
}

export function useSecretValue(name: string) {
  return useQuery({
    queryKey: [...SECRETS_QUERY_KEY, name],
    queryFn: () => getSecretValue(name),
    enabled: false,
  });
}

export function useSecretNames() {
  return useQuery({
    queryKey: SECRETS_QUERY_KEY,
    queryFn: getSecretNames,
  });
}

export function useSetSecretValueMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ name, value }: { name: string; value: string }) =>
      setSecretValue(name, value),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: SECRETS_QUERY_KEY,
        exact: true,
      });
    },
  });
}

export function useDeleteSecretValueMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ name }: { name: string }) => deleteSecretValue(name),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: SECRETS_QUERY_KEY,
        exact: true,
      });
    },
  });
}
