import { act, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import * as routes from '../routes/generator-configs';
import { GeneratorConfig } from '../routes/generator-configs/schemas';
import {
  useCreateGeneratorConfigMutation,
  useDeleteGeneratorConfigMutation,
  useGeneratorConfig,
  useGeneratorDirs,
  useImportGeneratorProjectMutation,
  usePutGeneratorFileMutation,
  useRenameGeneratorConfigMutation,
  useUpdateGeneratorConfigMutation,
  useUploadGeneratorFileMutation,
} from './useGeneratorConfigs';
import { renderHookWithClient } from '@/test/render';

vi.mock('../routes/generator-configs');

const CONFIG = {
  input: [{ timer: { seconds: 5, count: 1 } }],
  event: {
    template: {
      mode: 'all',
      templates: [{ main: { template: './templates/main.jinja' } }],
    },
  },
  output: [{ file: { path: './output/output.log' } }],
} as unknown as GeneratorConfig;

// The lists below hold mutations with different variables and
// results, so they are read through the one shape the assertions use.
type MutationHook = () => {
  mutateAsync: (variables: never) => Promise<unknown>;
};

const DIRS_KEY = ['generator-config-dirs'];
const DIRS_EXTENDED_KEY = ['generator-config-dirs-extended'];
const FILES_KEY = ['generator-config-dir-files'];

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(routes.listGeneratorDirs).mockResolvedValue(['web']);
  vi.mocked(routes.getGeneratorConfig).mockResolvedValue(CONFIG);
  vi.mocked(routes.createGeneratorConfig).mockResolvedValue();
  vi.mocked(routes.updateGeneratorConfig).mockResolvedValue();
  vi.mocked(routes.deleteGeneratorConfig).mockResolvedValue();
  vi.mocked(routes.renameGeneratorConfig).mockResolvedValue(['web']);
  vi.mocked(routes.importGeneratorProject).mockResolvedValue();
  vi.mocked(routes.uploadGeneratorFile).mockResolvedValue();
  vi.mocked(routes.putGeneratorFile).mockResolvedValue();
});

/**
 * Two lists of projects are cached side by side - the plain names and
 * the extended rows the projects table draws - and screens read one or
 * the other. A mutation that refreshes only one of them leaves the
 * other showing a project that is gone, or missing one that exists.
 */
describe('the two project lists', () => {
  it('are cached apart, so the extended one is not served for names', async () => {
    const { result, queryClient } = renderHookWithClient(() => ({
      names: useGeneratorDirs(false),
      rows: useGeneratorDirs(true),
    }));

    await waitFor(() => expect(result.current.names.isSuccess).toBe(true));

    expect(queryClient.getQueryData(DIRS_KEY)).toBeDefined();
    expect(queryClient.getQueryData(DIRS_EXTENDED_KEY)).toBeDefined();
    expect(routes.listGeneratorDirs).toHaveBeenCalledWith(false);
    expect(routes.listGeneratorDirs).toHaveBeenCalledWith(true);
  });

  it.each([
    [
      'creating a project',
      useCreateGeneratorConfigMutation as MutationHook,
      { name: 'api', config: CONFIG },
    ],
    [
      'deleting a project',
      useDeleteGeneratorConfigMutation as MutationHook,
      { name: 'web' },
    ],
    [
      'renaming a project',
      useRenameGeneratorConfigMutation as MutationHook,
      { name: 'web', newName: 'api' },
    ],
  ])('both go stale after %s', async (_label, hook, variables) => {
    const { result, queryClient } = renderHookWithClient(hook);

    queryClient.setQueryData(DIRS_KEY, ['web']);
    queryClient.setQueryData(DIRS_EXTENDED_KEY, []);

    await act(async () => {
      await result.current.mutateAsync(variables as never);
    });

    expect(queryClient.getQueryState(DIRS_KEY)?.isInvalidated).toBe(true);
    expect(queryClient.getQueryState(DIRS_EXTENDED_KEY)?.isInvalidated).toBe(
      true
    );
  });

  it('both go stale after a project is imported', async () => {
    const { result, queryClient } = renderHookWithClient(
      useImportGeneratorProjectMutation
    );

    queryClient.setQueryData(DIRS_KEY, ['web']);
    queryClient.setQueryData(DIRS_EXTENDED_KEY, []);

    await act(async () => {
      await result.current.mutateAsync({
        name: 'api',
        archive: new File(['zip'], 'api.zip'),
      });
    });

    expect(queryClient.getQueryState(DIRS_KEY)?.isInvalidated).toBe(true);
    expect(queryClient.getQueryState(DIRS_EXTENDED_KEY)?.isInvalidated).toBe(
      true
    );
  });
});

/**
 * A project cache is keyed by name and outlives the project itself, so
 * anything left from a deleted one would be served for the next project
 * that reuses the name. Those entries are dropped rather than marked
 * stale.
 */
describe('caches of a project that is gone', () => {
  it.each([
    [
      'deleted',
      useDeleteGeneratorConfigMutation as MutationHook,
      { name: 'web' },
    ],
    [
      'renamed',
      useRenameGeneratorConfigMutation as MutationHook,
      { name: 'web', newName: 'api' },
    ],
  ])('are dropped once the project is %s', async (_label, hook, variables) => {
    const { result, queryClient } = renderHookWithClient(hook);

    queryClient.setQueryData([...DIRS_KEY, 'web'], CONFIG);
    queryClient.setQueryData([...FILES_KEY, 'web'], []);

    await act(async () => {
      await result.current.mutateAsync(variables as never);
    });

    expect(queryClient.getQueryData([...DIRS_KEY, 'web'])).toBeUndefined();
    expect(queryClient.getQueryData([...FILES_KEY, 'web'])).toBeUndefined();
  });

  it('leaves another project untouched', async () => {
    const { result, queryClient } = renderHookWithClient(
      useDeleteGeneratorConfigMutation
    );

    queryClient.setQueryData([...DIRS_KEY, 'db'], CONFIG);

    await act(async () => {
      await result.current.mutateAsync({ name: 'web' });
    });

    expect(queryClient.getQueryData([...DIRS_KEY, 'db'])).toBeDefined();
  });
});

/**
 * A rename moves the path the startup entries and the running
 * instances point at, so those caches are no longer current either.
 */
describe('useRenameGeneratorConfigMutation', () => {
  it('stales the startup list and the instance list', async () => {
    const { result, queryClient } = renderHookWithClient(
      useRenameGeneratorConfigMutation
    );

    queryClient.setQueryData(['startup'], []);
    queryClient.setQueryData(['generators'], []);

    await act(async () => {
      await result.current.mutateAsync({ name: 'web', newName: 'api' });
    });

    expect(queryClient.getQueryState(['startup'])?.isInvalidated).toBe(true);
    expect(queryClient.getQueryState(['generators'])?.isInvalidated).toBe(true);
  });
});

describe('editing one project', () => {
  it('stales only that project, not the lists', async () => {
    const { result, queryClient } = renderHookWithClient(
      useUpdateGeneratorConfigMutation
    );

    queryClient.setQueryData(DIRS_KEY, ['web']);
    queryClient.setQueryData([...DIRS_KEY, 'web'], CONFIG);

    await act(async () => {
      await result.current.mutateAsync({ name: 'web', config: CONFIG });
    });

    expect(queryClient.getQueryState([...DIRS_KEY, 'web'])?.isInvalidated).toBe(
      true
    );
    expect(queryClient.getQueryState(DIRS_KEY)?.isInvalidated).toBe(false);
  });

  it('serves the configuration under the project name', async () => {
    const { result, queryClient } = renderHookWithClient(() =>
      useGeneratorConfig('web')
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(queryClient.getQueryData([...DIRS_KEY, 'web'])).toEqual(CONFIG);
  });
});

describe('writing a file', () => {
  it.each([
    ['uploading', useUploadGeneratorFileMutation as MutationHook],
    ['replacing', usePutGeneratorFileMutation as MutationHook],
  ])('stales the file tree of the project after %s one', async (_l, hook) => {
    const { result, queryClient } = renderHookWithClient(hook);

    queryClient.setQueryData([...FILES_KEY, 'web'], []);

    await act(async () => {
      await result.current.mutateAsync({
        name: 'web',
        filepath: 'templates/main.jinja',
        content: 'body',
      } as never);
    });

    expect(
      queryClient.getQueryState([...FILES_KEY, 'web'])?.isInvalidated
    ).toBe(true);
  });
});
