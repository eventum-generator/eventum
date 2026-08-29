import { act, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import * as routes from '../routes/instance';
import { Settings } from '../routes/instance/schemas';
import {
  useInstanceSettings,
  useRestartInstanceMutation,
  useStopInstanceMutation,
  useUpdateInstanceSettingsMutation,
} from './useInstance';
import { renderHookWithClient } from '@/test/render';

vi.mock('../routes/instance');

const SETTINGS = {
  server: { host: '0.0.0.0', port: 9474 },
  generation: {},
  log: { level: 'info' },
  path: {
    logs: '/app/logs',
    startup: '/app/startup.yml',
    generators_dir: '/app/generators',
    keyring_cryptfile: '/app/cryptfile.cfg',
  },
} as unknown as Settings;

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(routes.getInstanceSettings).mockResolvedValue(SETTINGS);
  vi.mocked(routes.updateInstanceSettings).mockResolvedValue();
  vi.mocked(routes.stopInstance).mockResolvedValue();
  vi.mocked(routes.restartInstance).mockResolvedValue();
});

describe('useInstanceSettings', () => {
  it('serves the settings tree under its own key', async () => {
    const { result, queryClient } = renderHookWithClient(useInstanceSettings);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(queryClient.getQueryData(['instance', 'settings'])).toEqual(
      SETTINGS
    );
  });
});

/**
 * The endpoint answers with no body, so what the instance now holds is
 * only known by reading it back - it normalises what it stores and
 * restarts on it. The cached tree is therefore marked stale rather than
 * overwritten with the answer.
 */
describe('useUpdateInstanceSettingsMutation', () => {
  it('sends the settings it was given', async () => {
    const { result } = renderHookWithClient(useUpdateInstanceSettingsMutation);

    await act(async () => {
      await result.current.mutateAsync({ settings: SETTINGS });
    });

    expect(routes.updateInstanceSettings).toHaveBeenCalledWith(SETTINGS);
  });

  it('marks the cached settings stale once they are saved', async () => {
    const { result, queryClient } = renderHookWithClient(
      useUpdateInstanceSettingsMutation
    );

    queryClient.setQueryData(['instance', 'settings'], SETTINGS);

    await act(async () => {
      await result.current.mutateAsync({ settings: SETTINGS });
    });

    expect(
      queryClient.getQueryState(['instance', 'settings'])?.isInvalidated
    ).toBe(true);
  });

  it('keeps the cached settings until they are read again', async () => {
    const { result, queryClient } = renderHookWithClient(
      useUpdateInstanceSettingsMutation
    );

    queryClient.setQueryData(['instance', 'settings'], SETTINGS);

    await act(async () => {
      await result.current.mutateAsync({ settings: SETTINGS });
    });

    // Nothing observes the query here, so staleness alone does not
    // refetch - the page that does observe it reads once it mounts.
    expect(queryClient.getQueryData(['instance', 'settings'])).toEqual(
      SETTINGS
    );
  });

  it('leaves an unrelated cache entry alone', async () => {
    const { result, queryClient } = renderHookWithClient(
      useUpdateInstanceSettingsMutation
    );

    queryClient.setQueryData(['instance', 'info'], { app_version: '1.0.0' });

    await act(async () => {
      await result.current.mutateAsync({ settings: SETTINGS });
    });

    expect(queryClient.getQueryState(['instance', 'info'])?.isInvalidated).toBe(
      false
    );
  });
});

/**
 * Stopping or restarting takes the backend down, so there is nothing to
 * invalidate: the next request either fails or reaches a fresh process.
 */
describe('lifecycle mutations', () => {
  it('stops the instance without touching the cache', async () => {
    const { result, queryClient } = renderHookWithClient(
      useStopInstanceMutation
    );

    queryClient.setQueryData(['instance', 'settings'], SETTINGS);

    await act(async () => {
      await result.current.mutateAsync();
    });

    expect(routes.stopInstance).toHaveBeenCalledTimes(1);
    expect(
      queryClient.getQueryState(['instance', 'settings'])?.isInvalidated
    ).toBe(false);
  });

  it('restarts the instance', async () => {
    const { result } = renderHookWithClient(useRestartInstanceMutation);

    await act(async () => {
      await result.current.mutateAsync();
    });

    expect(routes.restartInstance).toHaveBeenCalledTimes(1);
  });
});
