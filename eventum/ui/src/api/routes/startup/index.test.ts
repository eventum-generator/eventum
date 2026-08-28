import { beforeEach, describe, expect, it, vi } from 'vitest';

import {
  addGeneratorToStartup,
  bulkDeleteGeneratorsFromStartup,
  deleteGeneratorFromStartup,
  getStartupGenerator,
  getStartupGenerators,
  updateGeneratorInStartup,
} from './index';
import { StartupGeneratorParametersSchema } from './schemas';
import { apiClient } from '@/api/client';
import { APIError } from '@/api/errors';

vi.mock('@/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

const get = vi.mocked(apiClient.get);
const post = vi.mocked(apiClient.post);
const put = vi.mocked(apiClient.put);
const del = vi.mocked(apiClient.delete);

const ENTRY = {
  id: 'web',
  path: '/generators/web/generator.yml',
  autostart: false,
  scenarios: [],
};

beforeEach(() => {
  for (const mock of [get, post, put, del]) {
    mock.mockReset();
    mock.mockResolvedValue({ data: undefined });
  }
});

describe('the startup list', () => {
  it('is read as a list of instance definitions', async () => {
    get.mockResolvedValue({ data: [ENTRY] });

    const entries = await getStartupGenerators();

    expect(get).toHaveBeenCalledWith('/startup/');
    expect(entries[0]?.id).toBe('web');
  });

  it('reads one definition by id', async () => {
    get.mockResolvedValue({ data: ENTRY });

    await expect(getStartupGenerator('web')).resolves.toMatchObject({
      id: 'web',
    });
    expect(get).toHaveBeenCalledWith('/startup/web');
  });

  it('adds with a post and replaces with a put', async () => {
    await addGeneratorToStartup('web', ENTRY);
    await updateGeneratorInStartup('web', ENTRY);

    expect(post).toHaveBeenCalledWith('/startup/web', ENTRY);
    expect(put).toHaveBeenCalledWith('/startup/web', ENTRY);
  });

  it('deletes one definition by id', async () => {
    await deleteGeneratorFromStartup('web');

    expect(del).toHaveBeenCalledWith('/startup/web');
  });

  it('sends the ids of a bulk delete as the body', async () => {
    await bulkDeleteGeneratorsFromStartup(['web', 'db']);

    expect(post).toHaveBeenCalledWith('/startup/group-actions/bulk-delete', [
      'web',
      'db',
    ]);
  });
});

/**
 * A definition read back from the startup file carries only the fields
 * it was written with. The scenario list is the exception: an instance
 * that belongs to none has to read as an empty list rather than as
 * absent, since the screens group by it.
 */
describe('StartupGeneratorParametersSchema', () => {
  it('fills in an empty scenario list when the file names none', () => {
    const parsed = StartupGeneratorParametersSchema.parse({
      id: 'web',
      path: '/generators/web/generator.yml',
    });

    expect(parsed.scenarios).toEqual([]);
    expect(parsed.autostart).toBeUndefined();
  });

  it('keeps the scenarios a definition names', () => {
    const parsed = StartupGeneratorParametersSchema.parse({
      ...ENTRY,
      scenarios: ['corp'],
    });

    expect(parsed.scenarios).toEqual(['corp']);
  });

  it('requires an id, which the file keys the definition by', () => {
    expect(
      StartupGeneratorParametersSchema.safeParse({ path: '/p' }).success
    ).toBe(false);
  });

  it('rejects an empty id', () => {
    expect(
      StartupGeneratorParametersSchema.safeParse({ id: '', path: '/p' }).success
    ).toBe(false);
  });

  it('fails to read a list holding a definition without a path', async () => {
    get.mockResolvedValue({ data: [{ id: 'web' }] });

    await expect(getStartupGenerators()).rejects.toBeInstanceOf(APIError);
  });
});
