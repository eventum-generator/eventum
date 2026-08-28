import { act, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import * as routes from '../routes/scenarios';
import {
  useAddGeneratorToScenarioMutation,
  useClearScenarioGlobalStateMutation,
  useDeleteScenarioGlobalStateKeyMutation,
  useDeleteScenarioMutation,
  useRemoveGeneratorFromScenarioMutation,
  useRenameScenarioMutation,
  useScenarioGlobalState,
  useScenarios,
  useUpdateScenarioGlobalStateMutation,
} from './useScenarios';
import { renderHookWithClient } from '@/test/render';

vi.mock('../routes/scenarios');

type MutationHook = () => {
  mutateAsync: (variables: never) => Promise<unknown>;
};

// The global-state mutations are built for one scenario at a time.
type ScopedMutationHook = (name: string) => {
  mutateAsync: (variables: never) => Promise<unknown>;
};

const GLOBALS_KEY = ['scenarios', 'corp', 'global-state'];

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(routes.listScenarios).mockResolvedValue(['corp']);
  vi.mocked(routes.getScenarioGlobalState).mockResolvedValue({ counter: 1 });
  vi.mocked(routes.deleteScenario).mockResolvedValue();
  vi.mocked(routes.renameScenario).mockResolvedValue();
  vi.mocked(routes.addGeneratorToScenario).mockResolvedValue();
  vi.mocked(routes.removeGeneratorFromScenario).mockResolvedValue();
  vi.mocked(routes.updateScenarioGlobalState).mockResolvedValue();
  vi.mocked(routes.clearScenarioGlobalState).mockResolvedValue();
  vi.mocked(routes.deleteScenarioGlobalStateKey).mockResolvedValue();
});

describe('useScenarios', () => {
  it('serves the scenario names under their own key', async () => {
    const { result, queryClient } = renderHookWithClient(useScenarios);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(queryClient.getQueryData(['scenarios'])).toEqual(['corp']);
  });
});

/**
 * A scenario is stored as a list of instance ids on the startup
 * definitions, so every change to its membership - or to the scenario
 * itself - stales both the scenario list and the startup file.
 */
describe('changes to scenario membership', () => {
  it.each([
    [
      'deleting a scenario',
      useDeleteScenarioMutation as MutationHook,
      { name: 'corp' },
    ],
    [
      'renaming a scenario',
      useRenameScenarioMutation as MutationHook,
      { name: 'corp', newName: 'corp-2' },
    ],
    [
      'adding an instance',
      useAddGeneratorToScenarioMutation as MutationHook,
      { name: 'corp', generatorId: 'web' },
    ],
    [
      'removing an instance',
      useRemoveGeneratorFromScenarioMutation as MutationHook,
      { name: 'corp', generatorId: 'web' },
    ],
  ])('stales both lists after %s', async (_label, hook, variables) => {
    const { result, queryClient } = renderHookWithClient(hook);

    queryClient.setQueryData(['scenarios'], ['corp']);
    queryClient.setQueryData(['startup'], []);

    await act(async () => {
      await result.current.mutateAsync(variables as never);
    });

    expect(queryClient.getQueryState(['scenarios'])?.isInvalidated).toBe(true);
    expect(queryClient.getQueryState(['startup'])?.isInvalidated).toBe(true);
  });
});

/**
 * The shared state of a scenario is keyed by the scenario, so an edit
 * to one must not stale another's.
 */
describe('the shared global state', () => {
  it('is served per scenario', async () => {
    const { result, queryClient } = renderHookWithClient(() =>
      useScenarioGlobalState('corp')
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(queryClient.getQueryData(GLOBALS_KEY)).toEqual({ counter: 1 });
  });

  it.each([
    [
      'merging into it',
      useUpdateScenarioGlobalStateMutation as ScopedMutationHook,
      { counter: 2 },
    ],
    [
      'clearing it',
      useClearScenarioGlobalStateMutation as ScopedMutationHook,
      undefined,
    ],
    [
      'dropping one key',
      useDeleteScenarioGlobalStateKeyMutation as ScopedMutationHook,
      'counter',
    ],
  ])('goes stale after %s', async (_label, hookFactory, variables) => {
    const otherKey = ['scenarios', 'other', 'global-state'];
    const { result, queryClient } = renderHookWithClient(() =>
      hookFactory('corp')
    );

    queryClient.setQueryData(GLOBALS_KEY, { counter: 1 });
    queryClient.setQueryData(otherKey, {});

    await act(async () => {
      await result.current.mutateAsync(variables as never);
    });

    expect(queryClient.getQueryState(GLOBALS_KEY)?.isInvalidated).toBe(true);
    expect(queryClient.getQueryState(otherKey)?.isInvalidated).toBe(false);
  });
});
