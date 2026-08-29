import { basename } from 'pathe';
import z from 'zod';

import {
  FileNode,
  FileNodesListSchema,
  GeneratorConfig,
  GeneratorConfigPathSchema,
  GeneratorConfigSchema,
  GeneratorDirsExtendedInfo,
  GeneratorDirsExtendedInfoSchema,
  GeneratorFileContent,
  GeneratorFileContentSchema,
  GeneratorIdsSchema,
} from './schemas';
import { TRANSFER_TIMEOUT, apiClient } from '@/api/client';
import '@/api/routes/instance/schemas';
import { validateResponse } from '@/api/wrappers';

export async function listGeneratorDirs(
  extended: true
): Promise<GeneratorDirsExtendedInfo>;

export async function listGeneratorDirs(extended: false): Promise<string[]>;

export async function listGeneratorDirs(
  extended: boolean
): Promise<GeneratorDirsExtendedInfo | string[]>;

export async function listGeneratorDirs(
  extended: boolean
): Promise<GeneratorDirsExtendedInfo | string[]> {
  const ValidationSchema = extended
    ? GeneratorDirsExtendedInfoSchema
    : z.array(z.string());

  return await validateResponse(
    ValidationSchema,
    apiClient.get('/generator-configs/', {
      params: { extended: extended },
    })
  );
}

export async function getGeneratorConfig(
  name: string
): Promise<GeneratorConfig> {
  return await validateResponse(
    GeneratorConfigSchema,
    apiClient.get(`/generator-configs/${name}`)
  );
}

export async function createGeneratorConfig(
  name: string,
  config: GeneratorConfig
) {
  await apiClient.post(`/generator-configs/${name}`, config);
}

export async function updateGeneratorConfig(
  name: string,
  config: GeneratorConfig
) {
  await apiClient.put(`/generator-configs/${name}`, config);
}

export async function deleteGeneratorConfig(name: string) {
  await apiClient.delete(`/generator-configs/${name}`);
}

export async function renameGeneratorConfig(
  name: string,
  newName: string
): Promise<string[]> {
  return await validateResponse(
    GeneratorIdsSchema,
    apiClient.post(`/generator-configs/${encodeURIComponent(name)}/rename`, {
      new_name: newName,
    })
  );
}

export function getGeneratorProjectExportUrl(
  name: string,
  exclude: string[] = []
): string {
  return apiClient.getUri({
    url: `/generator-configs/${encodePathSegment(name)}/export`,
    params: exclude.length > 0 ? { exclude } : undefined,
    // Repeats the key per value (`exclude=a&exclude=b`), which is the
    // shape the backend reads a list of query values in.
    paramsSerializer: { indexes: null },
  });
}

export async function importGeneratorProject(name: string, archive: File) {
  const form = new FormData();
  form.append('content', archive, archive.name);

  await apiClient.post(
    `/generator-configs/${encodePathSegment(name)}/import`,
    form,
    {
      headers: {
        'Content-Type': undefined,
      },
      timeout: TRANSFER_TIMEOUT,
    }
  );
}

export async function getGeneratorConfigPath(name: string): Promise<string> {
  return await validateResponse(
    GeneratorConfigPathSchema,
    apiClient.get(`/generator-configs/${name}/path`)
  );
}

export async function getGeneratorFileTree(name: string): Promise<FileNode[]> {
  return (await validateResponse(
    FileNodesListSchema,
    apiClient.get(`/generator-configs/${name}/file-tree`)
  )) as FileNode[];
}

export async function getGeneratorFile(
  name: string,
  filepath: string
): Promise<GeneratorFileContent> {
  return await validateResponse(
    GeneratorFileContentSchema,
    apiClient.get(`/generator-configs/${name}/file/${filepath}`, {
      responseType: 'text',
      timeout: TRANSFER_TIMEOUT,
    })
  );
}

/**
 * Build the URL a browser downloads a project file from.
 *
 * The transfer goes through a plain navigation rather than the API client:
 * the browser streams the response straight to disk, while reading it here
 * would hold the whole file in memory - the very thing the editor size limit
 * avoids. Being same origin, the navigation carries the session cookie.
 */
export function getGeneratorFileDownloadUrl(
  name: string,
  filepath: string
): string {
  return apiClient.getUri({
    url: `/generator-configs/${encodePathSegment(name)}/file/${encodeFilePath(
      filepath
    )}`,
    params: { download: true },
  });
}

// A name reaches the URL as typed by whoever created the file, so every
// character that carries meaning in a URL - '#', '?', '%', a space - is
// escaped. Separators are kept, since the path is a path.
function encodeFilePath(filepath: string): string {
  return filepath
    .split('/')
    .map((segment) => encodePathSegment(segment))
    .join('/');
}

function encodePathSegment(segment: string): string {
  return encodeURIComponent(segment);
}

export async function uploadGeneratorFile(
  name: string,
  filepath: string,
  content: string | File
) {
  const form = new FormData();
  if (typeof content === 'string') {
    const filename = basename(filepath);
    form.append(
      'content',
      new Blob([content], { type: 'text/plain' }),
      filename
    );
  } else {
    form.append('content', content, content.name);
  }

  await apiClient.post(`/generator-configs/${name}/file/${filepath}`, form, {
    headers: {
      'Content-Type': undefined,
    },
    timeout: TRANSFER_TIMEOUT,
  });
}

export async function createGeneratorDirectory(name: string, dirpath: string) {
  await apiClient.post(`/generator-configs/${name}/file-makedir/${dirpath}`);
}

export async function putGeneratorFile(
  name: string,
  filepath: string,
  content: string
) {
  const form = new FormData();
  const filename = basename(filepath);
  form.append('content', new Blob([content], { type: 'text/plain' }), filename);

  await apiClient.put(`/generator-configs/${name}/file/${filepath}`, form, {
    headers: {
      'Content-Type': undefined,
    },
    timeout: TRANSFER_TIMEOUT,
  });
}

export async function deleteGeneratorFile(name: string, filepath: string) {
  await apiClient.delete(`/generator-configs/${name}/file/${filepath}`);
}

export async function moveGeneratorFile(
  name: string,
  source: string,
  destination: string
) {
  await apiClient.post(`/generator-configs/${name}/file-move`, undefined, {
    params: {
      source,
      destination,
    },
  });
}

export async function copyGeneratorFile(
  name: string,
  source: string,
  destination: string
) {
  await apiClient.post(
    `/generator-configs/${name}/file-copy`,
    {
      source,
      destination,
    },
    { timeout: TRANSFER_TIMEOUT }
  );
}
