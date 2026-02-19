import {
  UseQueryResult,
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query';

import {
  GeneratorConfig,
  GeneratorDirsExtendedInfo,
} from '../routes/generator-configs/schemas';
import {
  copyGeneratorFile,
  createGeneratorConfig,
  createGeneratorDirectory,
  deleteGeneratorConfig,
  deleteGeneratorFile,
  getGeneratorConfig,
  getGeneratorConfigPath,
  getGeneratorFile,
  getGeneratorFileTree,
  listGeneratorDirs,
  moveGeneratorFile,
  putGeneratorFile,
  updateGeneratorConfig,
  uploadGeneratorFile,
} from '@/api/routes/generator-configs';

const GENERATOR_CONFIG_DIRS_QUERY_KEY = ['generator-config-dirs'];
const GENERATOR_CONFIG_DIRS_EXTENDED_QUERY_KEY = [
  'generator-config-dirs-extended',
];

const GENERATOR_CONFIG_DIRS_COMMON_QUERY_KEYS = [
  GENERATOR_CONFIG_DIRS_QUERY_KEY,
  GENERATOR_CONFIG_DIRS_EXTENDED_QUERY_KEY,
];

export function useGeneratorDirs(
  extended: false
): UseQueryResult<string[], Error>;

export function useGeneratorDirs(
  extended: true
): UseQueryResult<GeneratorDirsExtendedInfo, Error>;

export function useGeneratorDirs(
  extended: boolean
): UseQueryResult<GeneratorDirsExtendedInfo | string[], Error>;

export function useGeneratorDirs(extended: boolean) {
  return useQuery({
    queryKey: [
      ...(extended
        ? GENERATOR_CONFIG_DIRS_EXTENDED_QUERY_KEY
        : GENERATOR_CONFIG_DIRS_QUERY_KEY),
    ],
    queryFn: () => listGeneratorDirs(extended),
  });
}

export function useGeneratorConfig(name: string) {
  return useQuery({
    queryKey: [...GENERATOR_CONFIG_DIRS_QUERY_KEY, name],
    queryFn: () => getGeneratorConfig(name),
  });
}

export function useCreateGeneratorConfigMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ name, config }: { name: string; config: GeneratorConfig }) =>
      createGeneratorConfig(name, config),
    onSuccess: async () => {
      await Promise.all(
        GENERATOR_CONFIG_DIRS_COMMON_QUERY_KEYS.map((key) =>
          queryClient.invalidateQueries({ queryKey: key, exact: true })
        )
      );
    },
  });
}

export function useUpdateGeneratorConfigMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ name, config }: { name: string; config: GeneratorConfig }) =>
      updateGeneratorConfig(name, config),
    onSuccess: async (_, { name }) => {
      await queryClient.invalidateQueries({
        queryKey: [...GENERATOR_CONFIG_DIRS_QUERY_KEY, name],
        exact: true,
      });
    },
  });
}

export function useDeleteGeneratorConfigMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ name }: { name: string }) => deleteGeneratorConfig(name),
    onSuccess: async () => {
      await Promise.all(
        GENERATOR_CONFIG_DIRS_COMMON_QUERY_KEYS.map((key) =>
          queryClient.invalidateQueries({ queryKey: key, exact: true })
        )
      );
    },
  });
}

export function useGeneratorConfigPathMutation() {
  return useMutation({
    mutationFn: ({ name }: { name: string }) => getGeneratorConfigPath(name),
  });
}

const GENERATOR_CONFIG_DIR_FILES_QUERY_KEY = ['generator-config-dir-files'];

export function useGeneratorFileTree(name: string) {
  return useQuery({
    queryKey: [...GENERATOR_CONFIG_DIR_FILES_QUERY_KEY, name],
    queryFn: () => getGeneratorFileTree(name),
  });
}

export function useGeneratorFileContent(name: string, filepath: string) {
  return useQuery({
    queryKey: [...GENERATOR_CONFIG_DIR_FILES_QUERY_KEY, name, filepath],
    queryFn: () => getGeneratorFile(name, filepath),
  });
}

export function useUploadGeneratorFileMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      name,
      filepath,
      content,
    }: {
      name: string;
      filepath: string;
      content: string | File;
    }) => uploadGeneratorFile(name, filepath, content),
    onSuccess: async (_, { name }) => {
      await queryClient.invalidateQueries({
        queryKey: [...GENERATOR_CONFIG_DIR_FILES_QUERY_KEY, name],
        exact: true,
      });
    },
  });
}

export function useCreateGeneratorDirectoryMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ name, dirpath }: { name: string; dirpath: string }) =>
      createGeneratorDirectory(name, dirpath),
    onSuccess: async (_, { name }) => {
      await queryClient.invalidateQueries({
        queryKey: [...GENERATOR_CONFIG_DIR_FILES_QUERY_KEY, name],
        exact: true,
      });
    },
  });
}

export function usePutGeneratorFileMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      name,
      filepath,
      content,
    }: {
      name: string;
      filepath: string;
      content: string;
    }) => putGeneratorFile(name, filepath, content),
    onSuccess: async (_, { name }) => {
      await queryClient.invalidateQueries({
        queryKey: [...GENERATOR_CONFIG_DIR_FILES_QUERY_KEY, name],
        exact: true,
      });
    },
  });
}

export function useDeleteGeneratorFileMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ name, filepath }: { name: string; filepath: string }) =>
      deleteGeneratorFile(name, filepath),
    onSuccess: async (_, { name }) => {
      await queryClient.invalidateQueries({
        queryKey: [...GENERATOR_CONFIG_DIR_FILES_QUERY_KEY, name],
        exact: true,
      });
    },
  });
}

export function useMoveGeneratorFileMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      name,
      source,
      destination,
    }: {
      name: string;
      source: string;
      destination: string;
    }) => moveGeneratorFile(name, source, destination),
    onSuccess: async (_, { name }) => {
      await queryClient.invalidateQueries({
        queryKey: [...GENERATOR_CONFIG_DIR_FILES_QUERY_KEY, name],
        exact: true,
      });
    },
  });
}

export function useCopyGeneratorFileMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      name,
      source,
      destination,
    }: {
      name: string;
      source: string;
      destination: string;
    }) => copyGeneratorFile(name, source, destination),
    onSuccess: async (_, { name }) => {
      await queryClient.invalidateQueries({
        queryKey: [...GENERATOR_CONFIG_DIR_FILES_QUERY_KEY, name],
        exact: true,
      });
    },
  });
}
