import { act, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import * as routes from '../routes/secrets';
import {
  useDeleteSecretValueMutation,
  useRenameSecretMutation,
  useSecretNames,
  useSecretReferences,
  useSecretValue,
  useSetSecretValueMutation,
} from './useSecrets';
import { renderHookWithClient } from '@/test/render';

vi.mock('../routes/secrets');

type MutationHook = () => {
  mutateAsync: (variables: never) => Promise<unknown>;
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(routes.getSecretNames).mockResolvedValue(['git_token']);
  vi.mocked(routes.getSecretValue).mockResolvedValue('token');
  // A secret is referenced from two places, and each is answered
  // separately: the projects that read it and the repositories that
  // authenticate with it.
  vi.mocked(routes.getSecretReferences).mockResolvedValue({
    projects: ['web'],
    repositories: [],
  });
  vi.mocked(routes.setSecretValue).mockResolvedValue();
  vi.mocked(routes.deleteSecretValue).mockResolvedValue();
  vi.mocked(routes.renameSecret).mockResolvedValue({
    projects: ['web'],
    repositories: [],
  });
});

describe('useSecretNames', () => {
  it('serves the names under the secrets key', async () => {
    const { result, queryClient } = renderHookWithClient(useSecretNames);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(queryClient.getQueryData(['secrets'])).toEqual(['git_token']);
  });
});

/**
 * A secret value is never fetched because a screen mounted: revealing
 * one is an explicit action, and the value only travels when the user
 * asks for it.
 */
describe('useSecretValue', () => {
  it('does not read the value on its own', () => {
    renderHookWithClient(() => useSecretValue('git_token'));

    expect(routes.getSecretValue).not.toHaveBeenCalled();
  });

  // The value is handed back by the fetch itself rather than kept on
  // the hook: a query that is never enabled has no result to read, and
  // the screens take it from what the fetch resolves with.
  it('hands the value back to whoever asked for it', async () => {
    const { result } = renderHookWithClient(() => useSecretValue('git_token'));

    let fetched: string | undefined;

    await act(async () => {
      fetched = (await result.current.refetch()).data;
    });

    expect(routes.getSecretValue).toHaveBeenCalledWith('git_token');
    expect(fetched).toBe('token');
  });
});

/**
 * The references are read to warn before a secret in use is deleted,
 * and only then - the screen asks for them when the dialog opens.
 */
describe('useSecretReferences', () => {
  it('does not read the references until enabled', () => {
    renderHookWithClient(() => useSecretReferences('git_token', false));

    expect(routes.getSecretReferences).not.toHaveBeenCalled();
  });

  it('reads them once enabled', async () => {
    const { result } = renderHookWithClient(() =>
      useSecretReferences('git_token', true)
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(routes.getSecretReferences).toHaveBeenCalledWith('git_token');
  });
});

/**
 * Every screen offering a secret reads the name list, so a write has to
 * stale it. The values are deliberately left alone: they are fetched on
 * demand and never served from the cache without one.
 */
describe('writing secrets', () => {
  it.each([
    [
      'setting a value',
      useSetSecretValueMutation as MutationHook,
      { name: 'git_token', value: 'new' },
    ],
    [
      'deleting one',
      useDeleteSecretValueMutation as MutationHook,
      { name: 'git_token' },
    ],
    [
      'renaming one',
      useRenameSecretMutation as MutationHook,
      { name: 'git_token', newName: 'token' },
    ],
  ])('stales the name list after %s', async (_label, hook, args) => {
    const { result, queryClient } = renderHookWithClient(hook);

    queryClient.setQueryData(['secrets'], ['git_token']);
    queryClient.setQueryData(['secrets', 'git_token'], 'token');

    await act(async () => {
      await result.current.mutateAsync(args as never);
    });

    expect(queryClient.getQueryState(['secrets'])?.isInvalidated).toBe(true);
    expect(
      queryClient.getQueryState(['secrets', 'git_token'])?.isInvalidated
    ).toBe(false);
  });
});
