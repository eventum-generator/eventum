import { basename } from 'pathe';
import { useCallback } from 'react';

import { getGeneratorFileDownloadUrl } from '@/api/routes/generator-configs';
import { useProjectName } from '@/pages/ProjectPage/hooks/useProjectName';
import { downloadUrl } from '@/utils/download';

/**
 * Save a file of the open project to the machine the browser runs on.
 *
 * The file is saved under its own name rather than the path it is addressed
 * by, since a path is not a name a file system accepts.
 */
export function useDownloadProjectFile(): (filepath: string) => void {
  const { projectName } = useProjectName();

  return useCallback(
    (filepath: string) =>
      downloadUrl(
        getGeneratorFileDownloadUrl(projectName, filepath),
        basename(filepath)
      ),
    [projectName]
  );
}
