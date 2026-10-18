import { beforeEach, describe, expect, it, vi } from 'vitest';

import {
  addGenerator,
  bulkRemoveGenerators,
  bulkStartGenerators,
  bulkStopGenerators,
  deleteGenerator,
  getGenerator,
  getGeneratorStatus,
  listGenerators,
  renameGenerator,
  startGenerator,
  stopGenerator,
  streamGeneratorLogs,
  updateGenerator,
} from './index';
import { GeneratorParameters } from './schemas';
import { STOP_TIMEOUT, apiClient } from '@/api/client';
import { APIError } from '@/api/errors';

vi.mock('@/api/client', async (importOriginal) => {
  const original = await importOriginal<typeof import('@/api/client')>();

  return {
    STOP_TIMEOUT: original.STOP_TIMEOUT,
    apiClient: {
      get: vi.fn(),
      post: vi.fn(),
      put: vi.fn(),
      delete: vi.fn(),
    },
  };
});

const get = vi.mocked(apiClient.get);
const post = vi.mocked(apiClient.post);
const put = vi.mocked(apiClient.put);
const del = vi.mocked(apiClient.delete);

const PARAMS: GeneratorParameters = {
  id: 'web',
  path: '/generators/web/generator.yml',
};

beforeEach(() => {
  for (const mock of [get, post, put, del]) {
    mock.mockReset();
    mock.mockResolvedValue({ data: undefined });
  }
});

describe('listGenerators', () => {
  it('returns the instances the backend knows', async () => {
    get.mockResolvedValue({
      data: [
        {
          id: 'web',
          path: '/generators/web/generator.yml',
          status: {
            is_initializing: false,
            is_running: true,
            is_ended_up: false,
            is_ended_up_successfully: false,
            is_stopping: false,
            is_abandoned: false,
          },
          start_time: '2026-08-20T10:00:00Z',
        },
      ],
    });

    const generators = await listGenerators();

    expect(get).toHaveBeenCalledWith('/generators/');
    expect(generators[0]?.status.is_running).toBe(true);
  });

  it('accepts an instance that has never started', async () => {
    get.mockResolvedValue({
      data: [
        {
          id: 'web',
          path: '/generators/web/generator.yml',
          status: {
            is_initializing: false,
            is_running: false,
            is_ended_up: false,
            is_ended_up_successfully: false,
            is_stopping: false,
            is_abandoned: false,
          },
          start_time: null,
        },
      ],
    });

    await expect(listGenerators()).resolves.toHaveLength(1);
  });

  it('rejects an instance without a status', async () => {
    get.mockResolvedValue({
      data: [{ id: 'web', path: '/p', start_time: null }],
    });

    const failure = await listGenerators().catch((error: unknown) => error);

    expect(failure).toBeInstanceOf(APIError);
    expect((failure as APIError).isResponseValidationError()).toBe(true);
  });

  it('rejects an instance with an empty id', async () => {
    get.mockResolvedValue({
      data: [
        {
          id: '',
          path: '/p',
          status: {
            is_initializing: false,
            is_running: false,
            is_ended_up: false,
            is_ended_up_successfully: false,
            is_stopping: false,
            is_abandoned: false,
          },
          start_time: null,
        },
      ],
    });

    await expect(listGenerators()).rejects.toBeInstanceOf(APIError);
  });
});

describe('getGeneratorStatus', () => {
  const STATUS = {
    is_initializing: false,
    is_running: true,
    is_ended_up: false,
    is_ended_up_successfully: false,
    is_stopping: false,
    is_abandoned: false,
  };

  it('returns an instance that a stop could not end', async () => {
    get.mockResolvedValue({ data: { ...STATUS, is_abandoned: true } });

    const status = await getGeneratorStatus('web');

    expect(get).toHaveBeenCalledWith('/generators/web/status');
    expect(status.is_abandoned).toBe(true);
    expect(status.is_running).toBe(true);
  });

  it('rejects a status that does not say whether it is stuck', async () => {
    // A backend older than the field leaves it out.
    get.mockResolvedValue({
      data: {
        is_initializing: false,
        is_running: true,
        is_ended_up: false,
        is_ended_up_successfully: false,
        is_stopping: false,
      },
    });

    await expect(getGeneratorStatus('web')).rejects.toBeInstanceOf(APIError);
  });
});

describe('getGenerator', () => {
  it('returns the parameters the instance was registered with', async () => {
    get.mockResolvedValue({ data: PARAMS });

    await expect(getGenerator('web')).resolves.toEqual(PARAMS);
    expect(get).toHaveBeenCalledWith('/generators/web');
  });
});

describe('writing an instance', () => {
  it('adds one with a post', async () => {
    await addGenerator('web', PARAMS);

    expect(post).toHaveBeenCalledWith('/generators/web', PARAMS);
  });

  it('updates one with a put, so a missing instance is not created', async () => {
    await updateGenerator('web', PARAMS);

    expect(put).toHaveBeenCalledWith('/generators/web', PARAMS);
  });

  it('deletes one by id', async () => {
    await deleteGenerator('web');

    expect(del).toHaveBeenCalledWith('/generators/web', {
      timeout: STOP_TIMEOUT,
    });
  });

  it('escapes an id that would otherwise change the path it renames', async () => {
    await renameGenerator('web/prod', 'web-prod');

    expect(post).toHaveBeenCalledWith('/generators/web%2Fprod/rename', {
      new_id: 'web-prod',
    });
  });
});

describe('lifecycle actions', () => {
  it('starts and stops one instance by id', async () => {
    await startGenerator('web');
    await stopGenerator('web');

    expect(post).toHaveBeenNthCalledWith(1, '/generators/web/start');
    expect(post).toHaveBeenNthCalledWith(2, '/generators/web/stop', undefined, {
      timeout: STOP_TIMEOUT,
    });
  });

  it('reports which of the started instances came up', async () => {
    post.mockResolvedValue({
      data: {
        running_generator_ids: ['web'],
        non_running_generator_ids: ['db'],
      },
    });

    const result = await bulkStartGenerators(['web', 'db']);

    expect(post).toHaveBeenCalledWith('/generators/group-actions/bulk-start', [
      'web',
      'db',
    ]);
    expect(result.non_running_generator_ids).toEqual(['db']);
  });

  it('sends the ids to stop as the body, not as a query', async () => {
    await bulkStopGenerators(['web']);

    expect(post).toHaveBeenCalledWith(
      '/generators/group-actions/bulk-stop',
      ['web'],
      { timeout: STOP_TIMEOUT }
    );
  });

  // A stop is bounded by the stop timeout of each generator, which may
  // run past the regular deadline of a request.
  it('waits for the backend to answer a stop rather than a fixed time', () => {
    expect(STOP_TIMEOUT).toBe(0);
  });

  it('removes instances without the regular deadline', async () => {
    post.mockResolvedValue({ data: { non_deleted_generator_ids: [] } });
    await bulkRemoveGenerators(['web']);

    expect(post).toHaveBeenCalledWith(
      '/generators/group-actions/bulk-delete',
      ['web'],
      { timeout: STOP_TIMEOUT }
    );
  });
});

describe('bulkRemoveGenerators', () => {
  it('reports the instances that did not stop', async () => {
    post.mockResolvedValue({ data: { non_deleted_generator_ids: ['web'] } });

    await expect(bulkRemoveGenerators(['web', 'db'])).resolves.toEqual({
      non_deleted_generator_ids: ['web'],
    });
  });

  it('rejects a response without the instances left', async () => {
    post.mockResolvedValue({ data: null });

    await expect(bulkRemoveGenerators(['web'])).rejects.toThrow();
  });
});

describe('streamGeneratorLogs', () => {
  it('opens the socket on the page host, carrying the offset', () => {
    const sockets: string[] = [];
    vi.stubGlobal(
      'WebSocket',
      class {
        constructor(url: string) {
          sockets.push(url);
        }
      }
    );

    streamGeneratorLogs('web', 512);

    expect(sockets[0]).toBe(
      `ws://${globalThis.location.host}/api/generators/web/logs?end_offset=512`
    );

    vi.unstubAllGlobals();
  });
});
