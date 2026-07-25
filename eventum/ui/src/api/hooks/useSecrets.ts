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
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: SECRETS_QUERY_KEY,
        exact: true,
      });
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
