import { act, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import * as routes from '../routes/repositories';
import { Catalog, Discovery } from '../routes/repositories/schemas';
import {
  useAddRepositoryMutation,
  useDeleteRepositoryMutation,
  useDiscoveredRepositories,
  useInstallGeneratorMutation,
  useRefreshCatalogMutation,
  useRepositoryCatalog,
} from './useRepositories';
import { renderHookWithClient } from '@/test/render';

vi.mock('../routes/repositories', async (importOriginal) => {
  const original =
    await importOriginal<typeof import('../routes/repositories')>();

  return {
    MAX_DISCOVERY_PAGES: original.MAX_DISCOVERY_PAGES,
    getRepositories: vi.fn(),
    addRepository: vi.fn(),
    deleteRepository: vi.fn(),
    checkRepository: vi.fn(),
    getCatalog: vi.fn(),
    refreshCatalog: vi.fn(),
    installGenerator: vi.fn(),
    discoverRepositories: vi.fn(),
  };
});

const CATALOG: Catalog = {
  revision: 'abc',
  refreshed_at: '2026-08-20T10:00:00Z',
  committed_at: '2026-08-20T09:00:00Z',
  author: null,
  entries: [],
};

function discovery(entries: number, total: number): Discovery {
  return {
    topic: 'eventum-generators',
    query: '',
    entries: Array.from({ length: entries }, (_, index) => ({
      name: `r${index}`,
      full_name: `owner/r${index}`,
      url: 'https://example.com',
      page_url: 'https://example.com',
      owner: 'owner',
      description: null,
      topics: [],
      stars: 0,
      updated_at: null,
      license: null,
      archived: false,
      official: false,
      connected: false,
    })),
    total_count: total,
    refreshed_at: '2026-08-20T10:00:00Z',
    rate: { remaining: null, reset_at: null },
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(routes.getRepositories).mockResolvedValue([]);
  vi.mocked(routes.getCatalog).mockResolvedValue(CATALOG);
  vi.mocked(routes.refreshCatalog).mockResolvedValue(CATALOG);
  vi.mocked(routes.addRepository).mockResolvedValue();
  vi.mocked(routes.deleteRepository).mockResolvedValue();
  vi.mocked(routes.installGenerator).mockResolvedValue();
  vi.mocked(routes.discoverRepositories).mockResolvedValue(discovery(0, 0));
});

/**
 * Reading a catalog reaches out to the remote through the backend, so
 * it is only read when a screen actually needs it and is not refetched
 * on its own afterwards.
 */
describe('useRepositoryCatalog', () => {
  it('does not read the catalog until enabled', () => {
    renderHookWithClient(() => useRepositoryCatalog('r', false));

    expect(routes.getCatalog).not.toHaveBeenCalled();
  });

  it('reads it once enabled, keyed by repository', async () => {
    const { result, queryClient } = renderHookWithClient(() =>
      useRepositoryCatalog('r', true)
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(queryClient.getQueryData(['repository-catalog', 'r'])).toEqual(
      CATALOG
    );
  });
});

/**
 * The published list marks which repositories are already connected, so
 * connecting or disconnecting one makes that list wrong as well.
 */
describe('connecting a repository', () => {
  it('stales the connected list and the published one', async () => {
    const { result, queryClient } = renderHookWithClient(
      useAddRepositoryMutation
    );

    queryClient.setQueryData(['repositories'], []);
    queryClient.setQueryData(['repository-discovery', ''], discovery(1, 1));

    await act(async () => {
      await result.current.mutateAsync({
        repository: { name: 'r', url: 'https://example.com/r' },
        verify: true,
      });
    });

    expect(queryClient.getQueryState(['repositories'])?.isInvalidated).toBe(
      true
    );
    expect(
      queryClient.getQueryState(['repository-discovery', ''])?.isInvalidated
    ).toBe(true);
  });

  it('drops the catalog of a repository that is disconnected', async () => {
    const { result, queryClient } = renderHookWithClient(
      useDeleteRepositoryMutation
    );

    queryClient.setQueryData(['repository-catalog', 'r'], CATALOG);
    queryClient.setQueryData(['repository-catalog', 'other'], CATALOG);

    await act(async () => {
      await result.current.mutateAsync('r');
    });

    expect(
      queryClient.getQueryData(['repository-catalog', 'r'])
    ).toBeUndefined();
    expect(
      queryClient.getQueryData(['repository-catalog', 'other'])
    ).toBeDefined();
  });
});

/**
 * A refresh returns the catalog it read, so writing it into the cache
 * saves reaching the remote a second time to display it.
 */
describe('useRefreshCatalogMutation', () => {
  it('caches the catalog it received', async () => {
    const { result, queryClient } = renderHookWithClient(
      useRefreshCatalogMutation
    );

    await act(async () => {
      await result.current.mutateAsync('r');
    });

    expect(queryClient.getQueryData(['repository-catalog', 'r'])).toEqual(
      CATALOG
    );
  });
});

/**
 * Installing writes a project directory. Anything cached for a project
 * of that name belongs to whatever was there before and must not be
 * served for what was just written.
 */
describe('useInstallGeneratorMutation', () => {
  it('drops what was cached for a project of the same name', async () => {
    const { result, queryClient } = renderHookWithClient(
      useInstallGeneratorMutation
    );

    queryClient.setQueryData(['generator-config-dirs', 'nginx'], {});
    queryClient.setQueryData(['generator-config-dir-files', 'nginx'], []);
    queryClient.setQueryData(['generator-config-dirs', 'other'], {});

    await act(async () => {
      await result.current.mutateAsync({
        name: 'r',
        entry: 'web/nginx',
        projectName: 'nginx',
      });
    });

    expect(
      queryClient.getQueryData(['generator-config-dirs', 'nginx'])
    ).toBeUndefined();
    expect(
      queryClient.getQueryData(['generator-config-dir-files', 'nginx'])
    ).toBeUndefined();
    expect(
      queryClient.getQueryData(['generator-config-dirs', 'other'])
    ).toBeDefined();
  });

  it('stales both project lists and every catalog', async () => {
    const { result, queryClient } = renderHookWithClient(
      useInstallGeneratorMutation
    );

    queryClient.setQueryData(['generator-config-dirs'], []);
    queryClient.setQueryData(['generator-config-dirs-extended'], []);
    queryClient.setQueryData(['repository-catalog', 'other'], CATALOG);

    await act(async () => {
      await result.current.mutateAsync({
        name: 'r',
        entry: 'web/nginx',
        projectName: 'nginx',
      });
    });

    expect(
      queryClient.getQueryState(['generator-config-dirs'])?.isInvalidated
    ).toBe(true);
    expect(
      queryClient.getQueryState(['generator-config-dirs-extended'])
        ?.isInvalidated
    ).toBe(true);
    expect(
      queryClient.getQueryState(['repository-catalog', 'other'])?.isInvalidated
    ).toBe(true);
  });
});

/**
 * The published list is paged, and the endpoint serves a bounded number
 * of pages. Asking past the end would come back refused, so the paging
 * has to stop on its own.
 */
describe('useDiscoveredRepositories', () => {
  it('offers no page after one that came back short', async () => {
    vi.mocked(routes.discoverRepositories).mockResolvedValue(discovery(0, 100));

    const { result } = renderHookWithClient(() =>
      useDiscoveredRepositories('', true)
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.hasNextPage).toBe(false);
  });

  it('offers no page once everything counted has been listed', async () => {
    vi.mocked(routes.discoverRepositories).mockResolvedValue(discovery(2, 2));

    const { result } = renderHookWithClient(() =>
      useDiscoveredRepositories('', true)
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.hasNextPage).toBe(false);
  });

  it('offers the next page while entries remain', async () => {
    vi.mocked(routes.discoverRepositories).mockResolvedValue(discovery(2, 50));

    const { result } = renderHookWithClient(() =>
      useDiscoveredRepositories('', true)
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.hasNextPage).toBe(true);
  });

  it('stops at the last page the endpoint serves', async () => {
    // Every page comes back full against a total far beyond what the
    // endpoint will serve, so only the page ceiling can end the paging.
    vi.mocked(routes.discoverRepositories).mockResolvedValue(
      discovery(2, 1000)
    );

    const { result } = renderHookWithClient(() =>
      useDiscoveredRepositories('', true)
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    while (result.current.hasNextPage) {
      await act(async () => {
        await result.current.fetchNextPage();
      });

      await waitFor(() =>
        expect(result.current.isFetchingNextPage).toBe(false)
      );
    }

    expect(result.current.data?.pages).toHaveLength(routes.MAX_DISCOVERY_PAGES);
  });

  it('does not search until enabled', () => {
    renderHookWithClient(() => useDiscoveredRepositories('nginx', false));

    expect(routes.discoverRepositories).not.toHaveBeenCalled();
  });
});
