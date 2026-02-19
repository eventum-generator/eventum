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
} from './schemas';
import { apiClient } from '@/api/client';
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
    })
  );
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
  await apiClient.post(`/generator-configs/${name}/file-copy`, {
    source,
    destination,
  });
}
