import { act, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import * as routes from '../routes/preview';
import {
  useClearTemplateEventPluginGlobalStateMutation,
  useClearTemplateEventPluginLocalStateMutation,
  useClearTemplateEventPluginSharedStateMutation,
  useDeleteTemplateEventPluginGlobalStateKeyMutation,
  useDeleteTemplateEventPluginLocalStateKeyMutation,
  useDeleteTemplateEventPluginSharedStateKeyMutation,
  useFormatEventsMutation,
  useGenerateTimestampsMutation,
  useInitializeEventPluginMutation,
  useNormalizedVersatileDatetimeMutation,
  useProduceEventsMutation,
  useReleaseEventPluginMutation,
  useTemplateEventPluginGlobalState,
  useTemplateEventPluginLocalState,
  useTemplateEventPluginSharedState,
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
  vi.mocked(routes.generateTimestamps).mockResolvedValue({
    timestamps: ['2026-08-20T10:00:00'],
    total_count: 1,
  } as never);
  vi.mocked(routes.initializeEventPlugin).mockResolvedValue();
  vi.mocked(routes.releaseEventPlugin).mockResolvedValue();
  vi.mocked(routes.formatEvents).mockResolvedValue({
    formatted_events: ['{}'],
    formatted_count: 1,
    errors: [],
  } as never);
  vi.mocked(routes.normalizeVersatileDatetime).mockResolvedValue(
    '2026-08-20T10:00:00+00:00'
  );
  vi.mocked(routes.getTemplateEventPluginLocalState).mockResolvedValue({
    attempt: 1,
  });
  vi.mocked(routes.getTemplateEventPluginSharedState).mockResolvedValue({
    session: 'abc',
  });
  vi.mocked(routes.getTemplateEventPluginGlobalState).mockResolvedValue({
    fleet: 3,
  });
  for (const fn of [
    routes.updateTemplateEventPluginLocalState,
    routes.deleteTemplateEventPluginSharedStateKey,
    routes.deleteTemplateEventPluginGlobalStateKey,
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

/**
 * The preview endpoints answer for a plugin instance the studio holds
 * open, so what matters per hook is that it addresses the right one: a
 * state is read under a key that names its scope and, for a local state,
 * the template it belongs to - two templates must not share an entry.
 */
describe('reading the state of a plugin instance', () => {
  it.each([
    [
      'a local state, under the template it belongs to',
      () => useTemplateEventPluginLocalState('web', 'main'),
      LOCAL_MAIN,
      { attempt: 1 },
    ],
    [
      'a shared state, under the generator',
      () => useTemplateEventPluginSharedState('web'),
      SHARED,
      { session: 'abc' },
    ],
    [
      'a global state, under the process',
      () => useTemplateEventPluginGlobalState('web'),
      GLOBAL,
      { fleet: 3 },
    ],
  ])('reads %s', async (_label, hook, key, expected) => {
    const { result, queryClient } = renderHookWithClient(hook);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(queryClient.getQueryData(key)).toEqual(expected);
  });

  it('keeps the local state of two templates apart', async () => {
    const { queryClient } = renderHookWithClient(() =>
      useTemplateEventPluginLocalState('web', 'main')
    );

    await waitFor(() =>
      expect(queryClient.getQueryData(LOCAL_MAIN)).toBeDefined()
    );

    expect(queryClient.getQueryData(LOCAL_OTHER)).toBeUndefined();
  });
});

/**
 * The tools of the console each ask the backend to do something with the
 * configuration being edited, and none of them caches: what they return
 * is read once and drawn.
 */
describe('the tools of the console', () => {
  it('generates timestamps from the input plugins as configured', async () => {
    const { result } = renderHookWithClient(useGenerateTimestampsMutation);

    await act(async () => {
      await result.current.mutateAsync({
        name: 'web',
        size: 10,
        skipPast: true,
        timezone: 'UTC',
        span: null,
        inputPluginsConfig: [{ timer: { seconds: 5, count: 1 } }] as never,
      });
    });

    // The route takes them apart rather than as one body.
    expect(routes.generateTimestamps).toHaveBeenCalledWith(
      'web',
      10,
      true,
      'UTC',
      null,
      [{ timer: { seconds: 5, count: 1 } }]
    );
  });

  it('opens and closes a plugin instance to debug against', async () => {
    const open = renderHookWithClient(useInitializeEventPluginMutation);

    await act(async () => {
      await open.result.current.mutateAsync({
        name: 'web',
        eventPluginConfig: {
          template: { mode: 'all', templates: [] },
        } as never,
      });
    });

    const close = renderHookWithClient(useReleaseEventPluginMutation);

    await act(async () => {
      await close.result.current.mutateAsync({ name: 'web' });
    });

    expect(routes.initializeEventPlugin).toHaveBeenCalledTimes(1);
    expect(routes.releaseEventPlugin).toHaveBeenCalledWith('web');
  });

  it('formats events through the formatter being configured', async () => {
    const { result } = renderHookWithClient(useFormatEventsMutation);

    await act(async () => {
      await result.current.mutateAsync({
        name: 'web',
        body: { events: ['{}'], formatter: { format: 'json' } } as never,
      });
    });

    expect(routes.formatEvents).toHaveBeenCalledWith(
      'web',
      expect.objectContaining({ events: ['{}'] })
    );
  });

  it('resolves what a versatile datetime expression means', async () => {
    const { result } = renderHookWithClient(
      useNormalizedVersatileDatetimeMutation
    );
    let resolved: unknown;

    await act(async () => {
      resolved = await result.current.mutateAsync({
        name: 'web',
        parameters: { value: 'now', timezone: 'UTC', none_point: 'now' },
      });
    });

    expect(resolved).toBe('2026-08-20T10:00:00+00:00');
  });
});

/**
 * Removing a key of a state is a write, so the entry that held it is
 * stale afterwards - and only that entry.
 */
describe('removing a key of a state', () => {
  it.each([
    [
      'a shared state',
      useDeleteTemplateEventPluginSharedStateKeyMutation,
      SHARED,
      GLOBAL,
    ],
    [
      'a global state',
      useDeleteTemplateEventPluginGlobalStateKeyMutation,
      GLOBAL,
      SHARED,
    ],
  ])(
    'marks %s stale and leaves the other alone',
    async (_label, hook, own, other) => {
      const { result, queryClient } = renderHookWithClient(
        hook as unknown as MutationHook
      );

      queryClient.setQueryData(own, { a: 1 });
      queryClient.setQueryData(other, { b: 2 });

      await act(async () => {
        await result.current.mutateAsync({
          name: 'web',
          key: 'a',
        } as never);
      });

      expect(queryClient.getQueryState(own)?.isInvalidated).toBe(true);
      expect(queryClient.getQueryState(other)?.isInvalidated).toBe(false);
    }
  );
});
