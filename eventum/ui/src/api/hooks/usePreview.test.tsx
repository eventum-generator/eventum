import { act } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import * as routes from '../routes/preview';
import {
  useClearTemplateEventPluginGlobalStateMutation,
  useClearTemplateEventPluginLocalStateMutation,
  useClearTemplateEventPluginSharedStateMutation,
  useDeleteTemplateEventPluginLocalStateKeyMutation,
  useProduceEventsMutation,
  useUpdateTemplateEventPluginGlobalStateMutation,
  useUpdateTemplateEventPluginLocalStateMutation,
  useUpdateTemplateEventPluginSharedStateMutation,
} from './usePreview';
import { renderHookWithClient } from '@/test/render';

vi.mock('../routes/preview');

type MutationHook = () => {
  mutateAsync: (variables: never) => Promise<unknown>;
};

const STATE_KEY = ['preview-event-plugin-template-state'];

const LOCAL_MAIN = [...STATE_KEY, 'web', 'local', 'main'];
const LOCAL_OTHER = [...STATE_KEY, 'web', 'local', 'other'];
const SHARED = [...STATE_KEY, 'web', 'shared'];
const GLOBAL = [...STATE_KEY, 'web', 'global'];

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(routes.produceEvents).mockResolvedValue({
    events: ['{}'],
    errors: [],
    exhausted: false,
  });
  for (const fn of [
    routes.updateTemplateEventPluginLocalState,
    routes.clearTemplateEventPluginLocalState,
    routes.deleteTemplateEventPluginLocalStateKey,
    routes.updateTemplateEventPluginSharedState,
    routes.clearTemplateEventPluginSharedState,
    routes.updateTemplateEventPluginGlobalState,
    routes.clearTemplateEventPluginGlobalState,
  ]) {
    vi.mocked(fn).mockResolvedValue();
  }
});

/**
 * The three state scopes a template can hold are cached apart, and the
 * local one apart per template. Editing one scope must not stale
 * another: they are shown side by side, and a refetch of the global
 * state reaches an endpoint that answers only while the debugger runs.
 */
describe('the template state scopes', () => {
  async function editWith(hook: MutationHook, variables: unknown) {
    const { result, queryClient } = renderHookWithClient(hook);

    for (const key of [LOCAL_MAIN, LOCAL_OTHER, SHARED, GLOBAL]) {
      queryClient.setQueryData(key, {});
    }

    await act(async () => {
      await result.current.mutateAsync(variables as never);
    });

    return queryClient;
  }

  it('stales one template local state, not another', async () => {
    const queryClient = await editWith(
      useUpdateTemplateEventPluginLocalStateMutation as MutationHook,
      { name: 'web', templateAlias: 'main', state: { a: 1 } }
    );

    expect(queryClient.getQueryState(LOCAL_MAIN)?.isInvalidated).toBe(true);
    expect(queryClient.getQueryState(LOCAL_OTHER)?.isInvalidated).toBe(false);
    expect(queryClient.getQueryState(SHARED)?.isInvalidated).toBe(false);
    expect(queryClient.getQueryState(GLOBAL)?.isInvalidated).toBe(false);
  });

  it('stales one template local state when it is cleared', async () => {
    const queryClient = await editWith(
      useClearTemplateEventPluginLocalStateMutation as MutationHook,
      { name: 'web', templateAlias: 'main' }
    );

    expect(queryClient.getQueryState(LOCAL_MAIN)?.isInvalidated).toBe(true);
    expect(queryClient.getQueryState(LOCAL_OTHER)?.isInvalidated).toBe(false);
  });

  it('stales one template local state when a key is dropped', async () => {
    const queryClient = await editWith(
      useDeleteTemplateEventPluginLocalStateKeyMutation as MutationHook,
      { name: 'web', templateAlias: 'main', key: 'a' }
    );

    expect(queryClient.getQueryState(LOCAL_MAIN)?.isInvalidated).toBe(true);
  });

  it.each([
    ['merged into', useUpdateTemplateEventPluginSharedStateMutation, { a: 1 }],
    ['cleared', useClearTemplateEventPluginSharedStateMutation, undefined],
  ])('stales only the shared state when it is %s', async (_l, hook, state) => {
    const queryClient = await editWith(hook as MutationHook, {
      name: 'web',
      state,
    });

    expect(queryClient.getQueryState(SHARED)?.isInvalidated).toBe(true);
    expect(queryClient.getQueryState(GLOBAL)?.isInvalidated).toBe(false);
    expect(queryClient.getQueryState(LOCAL_MAIN)?.isInvalidated).toBe(false);
  });

  it.each([
    ['merged into', useUpdateTemplateEventPluginGlobalStateMutation, { a: 1 }],
    ['cleared', useClearTemplateEventPluginGlobalStateMutation, undefined],
  ])('stales only the global state when it is %s', async (_l, hook, state) => {
    const queryClient = await editWith(hook as MutationHook, {
      name: 'web',
      state,
    });

    expect(queryClient.getQueryState(GLOBAL)?.isInvalidated).toBe(true);
    expect(queryClient.getQueryState(SHARED)?.isInvalidated).toBe(false);
  });
});

/**
 * Producing is a plain call against the running plugin instance - it
 * caches nothing, since the same parameters do not have to give the
 * same events twice.
 */
describe('useProduceEventsMutation', () => {
  it('returns what the plugin produced without caching it', async () => {
    const { result, queryClient } = renderHookWithClient(
      useProduceEventsMutation
    );

    let produced;

    await act(async () => {
      produced = await result.current.mutateAsync({
        name: 'web',
        produceParams: [{ timestamp: '2026-08-20T10:00:00', tags: [] }],
      });
    });

    expect(produced).toMatchObject({ events: ['{}'] });
    expect(queryClient.getQueryCache().getAll()).toHaveLength(0);
  });
});
