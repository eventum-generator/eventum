import { beforeEach, describe, expect, it, vi } from 'vitest';

import {
  deleteSecretValue,
  getSecretNames,
  getSecretReferences,
  getSecretValue,
  renameSecret,
  setSecretValue,
} from './index';
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

beforeEach(() => {
  for (const mock of [get, post, put, del]) {
    mock.mockReset();
    mock.mockResolvedValue({ data: undefined });
  }
});

describe('reading secrets', () => {
  it('lists the names the keyring holds', async () => {
    get.mockResolvedValue({ data: ['git_token', 'opensearch_password'] });

    await expect(getSecretNames()).resolves.toEqual([
      'git_token',
      'opensearch_password',
    ]);
    expect(get).toHaveBeenCalledWith('/secrets/');
  });

  it('reads one value by name', async () => {
    get.mockResolvedValue({ data: 'token' });

    await expect(getSecretValue('git_token')).resolves.toBe('token');
    expect(get).toHaveBeenCalledWith('/secrets/git_token');
  });

  it('rejects a value that is not a string', async () => {
    get.mockResolvedValue({ data: { value: 'token' } });

    await expect(getSecretValue('git_token')).rejects.toBeInstanceOf(APIError);
  });

  it('lists the projects a secret is referenced from', async () => {
    get.mockResolvedValue({ data: ['web'] });

    await expect(getSecretReferences('git token')).resolves.toEqual(['web']);
    expect(get).toHaveBeenCalledWith('/secrets/git%20token/references');
  });
});

/**
 * A secret value is a bare string, and the backend reads it as JSON. A
 * value with a quote or a backslash in it therefore has to be encoded
 * rather than sent raw, or the request body stops being valid JSON.
 */
describe('setSecretValue', () => {
  it('sends the value as a JSON string', async () => {
    await setSecretValue('git_token', 'token');

    expect(put).toHaveBeenCalledWith('/secrets/git_token', '"token"');
  });

  it('escapes a value that would otherwise break the body', async () => {
    await setSecretValue('git_token', String.raw`a"b\c`);

    expect(put).toHaveBeenCalledWith(
      '/secrets/git_token',
      String.raw`"a\"b\\c"`
    );
  });

  it('keeps an empty value distinguishable from an absent one', async () => {
    await setSecretValue('git_token', '');

    expect(put).toHaveBeenCalledWith('/secrets/git_token', '""');
  });
});

describe('writing secrets', () => {
  it('deletes one by name', async () => {
    await deleteSecretValue('git_token');

    expect(del).toHaveBeenCalledWith('/secrets/git_token');
  });

  it('escapes a name that would change the path it renames', async () => {
    await renameSecret('git token', 'git_token');

    expect(post).toHaveBeenCalledWith('/secrets/git%20token/rename', {
      new_name: 'git_token',
    });
  });
});
