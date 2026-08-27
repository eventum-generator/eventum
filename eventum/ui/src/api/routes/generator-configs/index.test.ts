import { beforeEach, describe, expect, it, vi } from 'vitest';

import {
  createGeneratorConfig,
  createGeneratorDirectory,
  deleteGeneratorConfig,
  deleteGeneratorFile,
  getGeneratorConfig,
  getGeneratorConfigPath,
  getGeneratorFile,
  getGeneratorFileTree,
  importGeneratorProject,
  listGeneratorDirs,
  moveGeneratorFile,
  putGeneratorFile,
  renameGeneratorConfig,
  updateGeneratorConfig,
  uploadGeneratorFile,
} from './index';
import { GeneratorConfig } from './schemas';
import { TRANSFER_TIMEOUT, apiClient } from '@/api/client';
import { APIError } from '@/api/errors';

vi.mock('@/api/client', async (importOriginal) => {
  const original = await importOriginal<typeof import('@/api/client')>();

  return {
    TRANSFER_TIMEOUT: original.TRANSFER_TIMEOUT,
    apiClient: {
      get: vi.fn(),
      post: vi.fn(),
      put: vi.fn(),
      delete: vi.fn(),
      getUri: original.apiClient.getUri.bind(original.apiClient),
    },
  };
});

const get = vi.mocked(apiClient.get);
const post = vi.mocked(apiClient.post);
const put = vi.mocked(apiClient.put);
const del = vi.mocked(apiClient.delete);

const CONFIG: GeneratorConfig = {
  input: [{ timer: { seconds: 5, count: 1 } }],
  event: {
    template: {
      mode: 'all',
      templates: [{ main: { template: './templates/main.jinja' } }],
    },
  },
  output: [{ file: { path: './output/output.log' } }],
} as unknown as GeneratorConfig;

beforeEach(() => {
  for (const mock of [get, post, put, del]) {
    mock.mockReset();
    mock.mockResolvedValue({ data: undefined });
  }
});

describe('listGeneratorDirs', () => {
  it('asks for names only when not extended', async () => {
    get.mockResolvedValue({ data: ['web', 'db'] });

    await expect(listGeneratorDirs(false)).resolves.toEqual(['web', 'db']);
    expect(get).toHaveBeenCalledWith('/generator-configs/', {
      params: { extended: false },
    });
  });

  it('validates the extended shape against the extended schema', async () => {
    get.mockResolvedValue({
      data: [
        {
          name: 'web',
          size_in_bytes: 10,
          last_modified: 1,
          generator_ids: ['web'],
        },
      ],
    });

    const dirs = await listGeneratorDirs(true);

    expect(dirs[0]?.generator_ids).toEqual(['web']);
  });

  it('rejects the extended shape when names were asked for', async () => {
    get.mockResolvedValue({
      data: [
        {
          name: 'web',
          size_in_bytes: 10,
          last_modified: 1,
          generator_ids: [],
        },
      ],
    });

    await expect(listGeneratorDirs(false)).rejects.toBeInstanceOf(APIError);
  });
});

describe('the project configuration', () => {
  it('is read back validated against the config schema', async () => {
    get.mockResolvedValue({ data: CONFIG });

    await expect(getGeneratorConfig('web')).resolves.toEqual(CONFIG);
    expect(get).toHaveBeenCalledWith('/generator-configs/web');
  });

  it('fails to read when the stored file lost a stage', async () => {
    get.mockResolvedValue({ data: { input: CONFIG.input } });

    await expect(getGeneratorConfig('web')).rejects.toBeInstanceOf(APIError);
  });

  it('is created with a post and replaced with a put', async () => {
    await createGeneratorConfig('web', CONFIG);
    await updateGeneratorConfig('web', CONFIG);

    expect(post).toHaveBeenCalledWith('/generator-configs/web', CONFIG);
    expect(put).toHaveBeenCalledWith('/generator-configs/web', CONFIG);
  });

  it('is deleted by name', async () => {
    await deleteGeneratorConfig('web');

    expect(del).toHaveBeenCalledWith('/generator-configs/web');
  });

  it('reports the instances a rename affected', async () => {
    post.mockResolvedValue({ data: ['web', 'web-2'] });

    await expect(renameGeneratorConfig('my web', 'web')).resolves.toEqual([
      'web',
      'web-2',
    ]);
    expect(post).toHaveBeenCalledWith('/generator-configs/my%20web/rename', {
      new_name: 'web',
    });
  });

  it('resolves the path the backend keeps the project at', async () => {
    get.mockResolvedValue({ data: '/generators/web/generator.yml' });

    await expect(getGeneratorConfigPath('web')).resolves.toBe(
      '/generators/web/generator.yml'
    );
  });
});

describe('project files', () => {
  it('reads the tree of a project', async () => {
    get.mockResolvedValue({
      data: [{ name: 'generator.yml', is_dir: false, size_in_bytes: 40 }],
    });

    const tree = await getGeneratorFileTree('web');

    expect(tree[0]?.name).toBe('generator.yml');
    expect(get).toHaveBeenCalledWith('/generator-configs/web/file-tree');
  });

  it('reads a file as text, without a deadline of its own', async () => {
    get.mockResolvedValue({ data: 'input: []' });

    await expect(getGeneratorFile('web', 'generator.yml')).resolves.toBe(
      'input: []'
    );
    expect(get).toHaveBeenCalledWith(
      '/generator-configs/web/file/generator.yml',
      { responseType: 'text', timeout: TRANSFER_TIMEOUT }
    );
  });

  it('uploads text content under the name of the file', async () => {
    await uploadGeneratorFile('web', 'templates/main.jinja', 'body');

    const [url, form, config] = post.mock.calls[0] as [
      string,
      FormData,
      { headers: Record<string, unknown>; timeout: number },
    ];

    expect(url).toBe('/generator-configs/web/file/templates/main.jinja');
    expect((form.get('content') as File).name).toBe('main.jinja');
    expect(config.headers['Content-Type']).toBeUndefined();
    expect(config.timeout).toBe(TRANSFER_TIMEOUT);
  });

  it('uploads a picked file under its own name', async () => {
    const picked = new File(['body'], 'events.json', { type: 'text/plain' });

    await uploadGeneratorFile('web', 'output/events.json', picked);

    const [, form] = post.mock.calls[0] as [string, FormData];

    expect((form.get('content') as File).name).toBe('events.json');
  });

  it('replaces a file with a put, so a missing one is not created', async () => {
    await putGeneratorFile('web', 'generator.yml', 'input: []');

    expect(put).toHaveBeenCalled();
    expect(put.mock.calls[0]?.[0]).toBe(
      '/generator-configs/web/file/generator.yml'
    );
  });

  it('deletes a file by its path inside the project', async () => {
    await deleteGeneratorFile('web', 'output/events.json');

    expect(del).toHaveBeenCalledWith(
      '/generator-configs/web/file/output/events.json'
    );
  });

  it('creates a directory through the makedir endpoint', async () => {
    await createGeneratorDirectory('web', 'templates/macros');

    expect(post).toHaveBeenCalledWith(
      '/generator-configs/web/file-makedir/templates/macros'
    );
  });

  it('moves a file by naming both ends as query values', async () => {
    await moveGeneratorFile('web', 'a.jinja', 'templates/a.jinja');

    expect(post).toHaveBeenCalledWith(
      '/generator-configs/web/file-move',
      undefined,
      { params: { source: 'a.jinja', destination: 'templates/a.jinja' } }
    );
  });
});

describe('importGeneratorProject', () => {
  it('sends the archive as form content with no deadline', async () => {
    const archive = new File(['zip'], 'web.zip', { type: 'application/zip' });

    await importGeneratorProject('my web', archive);

    const [url, form, config] = post.mock.calls[0] as [
      string,
      FormData,
      { timeout: number },
    ];

    expect(url).toBe('/generator-configs/my%20web/import');
    expect((form.get('content') as File).name).toBe('web.zip');
    expect(config.timeout).toBe(TRANSFER_TIMEOUT);
  });
});
