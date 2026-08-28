import { beforeEach, describe, expect, it, vi } from 'vitest';

import {
  MAX_DISCOVERY_PAGES,
  addRepository,
  checkRepository,
  deleteRepository,
  discoverRepositories,
  getCatalog,
  getRepositories,
  installGenerator,
  refreshCatalog,
} from './index';
import { apiClient } from '@/api/client';
import { APIError } from '@/api/errors';

vi.mock('@/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}));

const get = vi.mocked(apiClient.get);
const post = vi.mocked(apiClient.post);
const del = vi.mocked(apiClient.delete);

const STATUS = {
  state: 'available',
  checked_at: '2026-08-20T10:00:00Z',
  reason: null,
};

const CATALOG = {
  revision: 'abc123',
  refreshed_at: '2026-08-20T10:00:00Z',
  committed_at: '2026-08-19T09:00:00+02:00',
  author: 'someone',
  entries: [],
};

beforeEach(() => {
  for (const mock of [get, post, del]) {
    mock.mockReset();
    mock.mockResolvedValue({ data: undefined });
  }
});

describe('getRepositories', () => {
  it('returns the connected repositories with their status', async () => {
    get.mockResolvedValue({
      data: [
        {
          name: 'content-packs',
          url: 'https://github.com/eventum-generator/content-packs',
          status: STATUS,
        },
      ],
    });

    const repositories = await getRepositories();

    expect(get).toHaveBeenCalledWith('/repositories/');
    expect(repositories[0]?.status.state).toBe('available');
  });

  it('rejects a status the app has no state for', async () => {
    get.mockResolvedValue({
      data: [
        {
          name: 'r',
          url: 'https://example.com/r',
          status: { ...STATUS, state: 'flaky' },
        },
      ],
    });

    await expect(getRepositories()).rejects.toBeInstanceOf(APIError);
  });
});

/**
 * Adding a repository can verify it against the remote first, which
 * takes a network round trip on the backend. The flag travels as a
 * query parameter, so dropping it silently changes whether the user is
 * told about a bad URL now or only when the catalog is first read.
 */
describe('addRepository', () => {
  it('verifies by default', async () => {
    await addRepository({ name: 'r', url: 'https://example.com/r' });

    expect(post).toHaveBeenCalledWith(
      '/repositories/',
      { name: 'r', url: 'https://example.com/r' },
      { params: { verify: true } }
    );
  });

  it('skips verification when asked to', async () => {
    await addRepository({ name: 'r', url: 'https://example.com/r' }, false);

    expect(post.mock.calls[0]?.[2]).toEqual({ params: { verify: false } });
  });
});

describe('per-repository actions', () => {
  it('escapes the name when deleting one', async () => {
    await deleteRepository('my repo');

    expect(del).toHaveBeenCalledWith('/repositories/my%20repo');
  });

  it('escapes the name when checking one', async () => {
    post.mockResolvedValue({ data: STATUS });

    await checkRepository('my repo');

    expect(post).toHaveBeenCalledWith('/repositories/my%20repo/check');
  });

  it('escapes the name when reading a catalog', async () => {
    get.mockResolvedValue({ data: CATALOG });

    await getCatalog('my repo');

    expect(get).toHaveBeenCalledWith('/repositories/my%20repo/catalog');
  });

  it('escapes the name when refreshing a catalog', async () => {
    post.mockResolvedValue({ data: CATALOG });

    await refreshCatalog('my repo');

    expect(post).toHaveBeenCalledWith('/repositories/my%20repo/refresh');
  });

  it('accepts a repository that has never been checked', async () => {
    post.mockResolvedValue({
      data: { state: 'unknown', checked_at: null, reason: null },
    });

    await expect(checkRepository('r')).resolves.toMatchObject({
      state: 'unknown',
    });
  });

  it('accepts a commit moment carrying its own offset', async () => {
    get.mockResolvedValue({ data: CATALOG });

    await expect(getCatalog('r')).resolves.toMatchObject({
      revision: 'abc123',
    });
  });

  it('rejects a moment that is not a timestamp', async () => {
    get.mockResolvedValue({ data: { ...CATALOG, committed_at: 'yesterday' } });

    await expect(getCatalog('r')).rejects.toBeInstanceOf(APIError);
  });
});

describe('installGenerator', () => {
  it('escapes both the repository and the entry, naming the project', async () => {
    await installGenerator('my repo', 'web/nginx', 'nginx');

    expect(post).toHaveBeenCalledWith(
      '/repositories/my%20repo/catalog/web%2Fnginx/install',
      { name: 'nginx' }
    );
  });
});

describe('discoverRepositories', () => {
  const DISCOVERY = {
    topic: 'eventum-generators',
    query: 'nginx',
    entries: [],
    total_count: 0,
    refreshed_at: '2026-08-20T10:00:00Z',
    rate: { remaining: 9, reset_at: '2026-08-20T11:00:00Z' },
  };

  it('asks for the first page by default', async () => {
    get.mockResolvedValue({ data: DISCOVERY });

    await discoverRepositories('nginx');

    expect(get).toHaveBeenCalledWith('/repositories/discover', {
      params: { query: 'nginx', page: 1 },
    });
  });

  it('drops an empty query rather than searching for nothing', async () => {
    get.mockResolvedValue({ data: { ...DISCOVERY, query: '' } });

    await discoverRepositories('', 2);

    expect(get).toHaveBeenCalledWith('/repositories/discover', {
      params: { query: undefined, page: 2 },
    });
  });

  it('accepts a rate the backend could not read', async () => {
    get.mockResolvedValue({
      data: { ...DISCOVERY, rate: { remaining: null, reset_at: null } },
    });

    await expect(discoverRepositories('nginx')).resolves.toMatchObject({
      rate: { remaining: null },
    });
  });

  it('bounds the pages the endpoint serves', () => {
    expect(MAX_DISCOVERY_PAGES).toBeGreaterThan(0);
  });
});
