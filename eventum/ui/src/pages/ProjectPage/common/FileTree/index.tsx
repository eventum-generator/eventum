import { Alert, Skeleton, Stack } from '@mantine/core';
import { FC, useMemo } from 'react';

import { useProjectName } from '../../hooks/useProjectName';
import { Tree } from './Tree';
import { useGeneratorFileTree } from '@/api/hooks/useGeneratorConfigs';
import { createFileTreeLookup } from '@/api/routes/generator-configs/modules/file-tree';
import { AlertIcon } from '@/components/ui/AlertIcon';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';

export const FileTree: FC = () => {
  const { projectName } = useProjectName();
  const {
    data: fileTree,
    isLoading: isFileTreeLoading,
    isError: isFileTreeError,
    error: fileTreeError,
    isSuccess: isFileTreeSuccess,
  } = useGeneratorFileTree(projectName);

  const fileTreeLookup: ReturnType<typeof createFileTreeLookup> | null =
    useMemo(() => {
      if (isFileTreeSuccess) {
        return createFileTreeLookup(fileTree);
      } else {
        return null;
      }
    }, [fileTree, isFileTreeSuccess]);

  return (
    <Stack>
      {isFileTreeLoading && (
        <Stack>
          <Skeleton h="250px" animate visible />
        </Stack>
      )}

      {isFileTreeError && (
        <Alert
          variant="default"
          icon={<AlertIcon variant="error" />}
          title="Failed to load list of project files"
        >
          {fileTreeError.message}
          <ShowErrorDetailsAnchor error={fileTreeError} prependDot />
        </Alert>
      )}

      {isFileTreeSuccess && fileTreeLookup !== null && (
        <Tree fileTreeLookup={fileTreeLookup} />
      )}
    </Stack>
  );
};
