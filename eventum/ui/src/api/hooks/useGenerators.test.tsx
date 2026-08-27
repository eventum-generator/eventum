import { act, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import * as routes from '../routes/generators';
import { GeneratorsInfo } from '../routes/generators/schemas';
import {
  useAddGeneratorMutation,
  useBulkDeleteGeneratorMutation,
  useBulkStopGeneratorMutation,
  useDeleteGeneratorMutation,
  useGenerator,
  useGenerators,
  useRenameGeneratorMutation,
  useStartGeneratorMutation,
  useStopGeneratorMutation,
  useUpdateGeneratorMutation,
  useUpdateGeneratorStatus,
} from './useGenerators';
import { renderHookWithClient } from '@/test/render';

vi.mock('../routes/generators');

const IDLE = {
  is_initializing: false,
  is_running: false,
  is_ended_up: false,
  is_ended_up_successfully: false,
  is_stopping: false,
};

const GENERATORS: GeneratorsInfo = [
  { id: 'web', path: '/p/web', status: IDLE, start_time: null },
  { id: 'db', path: '/p/db', status: IDLE, start_time: null },
];

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(routes.listGenerators).mockResolvedValue(GENERATORS);
  vi.mocked(routes.getGenerator).mockResolvedValue({
    id: 'web',
    path: '/p/web',
  });
  vi.mocked(routes.addGenerator).mockResolvedValue();
  vi.mocked(routes.updateGenerator).mockResolvedValue();
  vi.mocked(routes.deleteGenerator).mockResolvedValue();
  vi.mocked(routes.renameGenerator).mockResolvedValue();
  vi.mocked(routes.startGenerator).mockResolvedValue();
  vi.mocked(routes.stopGenerator).mockResolvedValue();
  vi.mocked(routes.bulkStopGenerators).mockResolvedValue();
  vi.mocked(routes.bulkRemoveGenerators).mockResolvedValue();
});

describe('useGenerators', () => {
  it('serves the list under its own key', async () => {
    const { result, queryClient } = renderHookWithClient(() => useGenerators());

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(queryClient.getQueryData(['generators'])).toEqual(GENERATORS);
  });

  it('keys one instance under the list, so both can be invalidated at once', async () => {
    const { result, queryClient } = renderHookWithClient(() =>
      useGenerator('web')
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(queryClient.getQueryData(['generators', 'web'])).toMatchObject({
      id: 'web',
    });
  });

  it('refetches the list once a mutation invalidated it', async () => {
    const { result } = renderHookWithClient(() => ({
      list: useGenerators(),
      add: useAddGeneratorMutation(),
    }));

    await waitFor(() => expect(result.current.list.isSuccess).toBe(true));
    expect(routes.listGenerators).toHaveBeenCalledTimes(1);

    await act(async () => {
      await result.current.add.mutateAsync({
        id: 'api',
        params: { id: 'api', path: '/p/api' },
      });
    });

    await waitFor(() => expect(routes.listGenerators).toHaveBeenCalledTimes(2));
  });
});

/**
 * Every screen reads the instance list from the cache, so a mutation
 * that does not invalidate it leaves the table showing the state from
 * before the action - which reads as the action having failed.
 *
 * The list is seeded rather than queried here: with nothing observing
 * it, an invalidated entry stays marked instead of refetching at once,
 * which is what makes the assertion exact.
 */
describe('mutations that stale the list', () => {
  async function runMutation(
    hook: () => { mutateAsync: (variables: never) => Promise<unknown> },
    variables: unknown
  ) {
    const { result, queryClient } = renderHookWithClient(hook);

    queryClient.setQueryData(['generators'], GENERATORS);
    queryClient.setQueryData(['generators', 'web'], GENERATORS[0]);

    await act(async () => {
      await result.current.mutateAsync(variables as never);
    });

    return queryClient;
  }

  it.each([
    [
      'adding one',
      useAddGeneratorMutation,
      { id: 'api', params: { id: 'api', path: '/p' } },
    ],
    ['deleting one', useDeleteGeneratorMutation, { id: 'web' }],
    ['starting one', useStartGeneratorMutation, { id: 'web' }],
    ['stopping one', useStopGeneratorMutation, { id: 'web' }],
    ['stopping several', useBulkStopGeneratorMutation, { ids: ['web'] }],
    ['deleting several', useBulkDeleteGeneratorMutation, { ids: ['web'] }],
  ])('stales the list after %s', async (_label, hook, variables) => {
    const queryClient = await runMutation(hook, variables);

    expect(queryClient.getQueryState(['generators'])?.isInvalidated).toBe(true);
  });

  it('stales only the edited instance, not the whole list', async () => {
    const queryClient = await runMutation(useUpdateGeneratorMutation, {
      id: 'web',
      params: { id: 'web', path: '/p/web' },
    });

    expect(
      queryClient.getQueryState(['generators', 'web'])?.isInvalidated
    ).toBe(true);
    expect(queryClient.getQueryState(['generators'])?.isInvalidated).toBe(
      false
    );
  });

  it('stales the started instance along with the list', async () => {
    const queryClient = await runMutation(useStartGeneratorMutation, {
      id: 'web',
    });

    expect(
      queryClient.getQueryState(['generators', 'web'])?.isInvalidated
    ).toBe(true);
  });
});

/**
 * A rename moves the id the startup file and the scenarios refer to, so
 * those caches go stale together with the instance list.
 */
describe('useRenameGeneratorMutation', () => {
  it('invalidates the startup and scenario caches too', async () => {
    const { result, queryClient } = renderHookWithClient(() =>
      useRenameGeneratorMutation()
    );

    queryClient.setQueryData(['startup'], ['web']);
    queryClient.setQueryData(['scenarios'], ['corp']);

    await act(async () => {
      await result.current.mutateAsync({ id: 'web', newId: 'api' });
    });

    expect(queryClient.getQueryState(['startup'])?.isInvalidated).toBe(true);
    expect(queryClient.getQueryState(['scenarios'])?.isInvalidated).toBe(true);
  });
});

/**
 * Starting an instance takes a moment on the backend, so the table
 * shows the transition immediately by writing it into the cache. Only
 * the named instance may change, and nothing may be refetched - a
 * refetch would replace the transition with the state before it.
 */
describe('useUpdateGeneratorStatus', () => {
  it('marks one instance as starting, leaving the others as they were', async () => {
    const { result, queryClient } = renderHookWithClient(() =>
      useUpdateGeneratorStatus()
    );

    queryClient.setQueryData(['generators'], GENERATORS);

    await act(async () => {
      await result.current.mutateAsync({
        id: 'web',
        status: { ...IDLE, is_initializing: true },
      });
    });

    const cached = queryClient.getQueryData<GeneratorsInfo>(['generators']);

    expect(
      cached?.find((item) => item.id === 'web')?.status.is_initializing
    ).toBe(true);
    expect(
      cached?.find((item) => item.id === 'db')?.status.is_initializing
    ).toBe(false);
  });

  it('leaves the list valid, so nothing refetches over the transition', async () => {
    const { result, queryClient } = renderHookWithClient(() =>
      useUpdateGeneratorStatus()
    );

    queryClient.setQueryData(['generators'], GENERATORS);

    await act(async () => {
      await result.current.mutateAsync({
        id: 'web',
        status: { ...IDLE, is_running: true },
      });
    });

    expect(queryClient.getQueryState(['generators'])?.isInvalidated).toBe(
      false
    );
    expect(routes.listGenerators).not.toHaveBeenCalled();
  });
});
