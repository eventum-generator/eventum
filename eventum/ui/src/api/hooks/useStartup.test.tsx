import { act, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import * as routes from '../routes/startup';
import {
  useAddGeneratorToStartupMutation,
  useBulkDeleteGeneratorsFromStartupMutation,
  useDeleteGeneratorFromStartupMutation,
  useStartupGenerator,
  useStartupGenerators,
  useUpdateGeneratorInStartupMutation,
} from './useStartup';
import { renderHookWithClient } from '@/test/render';

vi.mock('../routes/startup');

const ENTRY = {
  id: 'web',
  path: '/generators/web/generator.yml',
  scenarios: [],
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(routes.getStartupGenerators).mockResolvedValue([ENTRY]);
  vi.mocked(routes.getStartupGenerator).mockResolvedValue(ENTRY);
  vi.mocked(routes.addGeneratorToStartup).mockResolvedValue();
  vi.mocked(routes.updateGeneratorInStartup).mockResolvedValue();
  vi.mocked(routes.deleteGeneratorFromStartup).mockResolvedValue();
  vi.mocked(routes.bulkDeleteGeneratorsFromStartup).mockResolvedValue();
});

describe('the startup list', () => {
  it('is served under its own key', async () => {
    const { result, queryClient } = renderHookWithClient(useStartupGenerators);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(queryClient.getQueryData(['startup'])).toEqual([ENTRY]);
  });

  it('keys one definition under the list', async () => {
    const { result, queryClient } = renderHookWithClient(() =>
      useStartupGenerator('web')
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(queryClient.getQueryData(['startup', 'web'])).toEqual(ENTRY);
  });
});

/**
 * The instances screen reads the startup list to know which instances
 * come up on their own, so a definition added or removed without the
 * list going stale leaves the screen contradicting the file.
 */
describe('mutations on the startup file', () => {
  it('stales the list after a definition is added', async () => {
    const { result, queryClient } = renderHookWithClient(
      useAddGeneratorToStartupMutation
    );

    queryClient.setQueryData(['startup'], [ENTRY]);

    await act(async () => {
      await result.current.mutateAsync({ id: 'api', params: ENTRY });
    });

    expect(queryClient.getQueryState(['startup'])?.isInvalidated).toBe(true);
  });

  it('stales the list after a definition is deleted', async () => {
    const { result, queryClient } = renderHookWithClient(
      useDeleteGeneratorFromStartupMutation
    );

    queryClient.setQueryData(['startup'], [ENTRY]);

    await act(async () => {
      await result.current.mutateAsync({ id: 'web' });
    });

    expect(queryClient.getQueryState(['startup'])?.isInvalidated).toBe(true);
  });

  it('stales the list after several are deleted at once', async () => {
    const { result, queryClient } = renderHookWithClient(
      useBulkDeleteGeneratorsFromStartupMutation
    );

    queryClient.setQueryData(['startup'], [ENTRY]);

    await act(async () => {
      await result.current.mutateAsync({ ids: ['web', 'db'] });
    });

    expect(queryClient.getQueryState(['startup'])?.isInvalidated).toBe(true);
  });

  it('stales only the edited definition when one is updated', async () => {
    const { result, queryClient } = renderHookWithClient(
      useUpdateGeneratorInStartupMutation
    );

    queryClient.setQueryData(['startup'], [ENTRY]);
    queryClient.setQueryData(['startup', 'web'], ENTRY);

    await act(async () => {
      await result.current.mutateAsync({ id: 'web', params: ENTRY });
    });

    expect(queryClient.getQueryState(['startup', 'web'])?.isInvalidated).toBe(
      true
    );
    expect(queryClient.getQueryState(['startup'])?.isInvalidated).toBe(false);
  });
});
