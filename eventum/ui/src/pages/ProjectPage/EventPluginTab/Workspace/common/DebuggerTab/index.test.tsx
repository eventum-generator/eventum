import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { DebuggerTab } from './index';
import {
  useInitializeEventPluginMutation,
  useProduceEventsMutation,
  useReleaseEventPluginMutation,
} from '@/api/hooks/usePreview';
import { EventPluginNamedConfig } from '@/api/routes/generator-configs/schemas/plugins/event';
import { ProducedEventsInfo } from '@/api/routes/preview/schemas';
import { GetPluginConfigProvider } from '@/pages/ProjectPage/EventPluginTab/context/GetPluginConfigContext';
import { ProjectNameProvider } from '@/pages/ProjectPage/context/ProjectNameContext';
import { renderWithProviders } from '@/test/render';

vi.mock('@/api/hooks/usePreview');

const CONFIG = {
  template: {
    mode: 'all',
    templates: [{ main: { template: './templates/main.jinja' } }],
  },
} as unknown as EventPluginNamedConfig;

interface Handlers {
  onSuccess?: (data?: unknown) => void;
  onError?: (error: Error) => void;
}

function mutation(result?: unknown, fails = false) {
  return {
    mutate: vi.fn((_variables: unknown, handlers?: Handlers) => {
      if (fails) {
        handlers?.onError?.(new Error('no connection'));
      } else {
        handlers?.onSuccess?.(result);
      }
    }),
    isPending: false,
  };
}

let initialize: ReturnType<typeof mutation>;
let release: ReturnType<typeof mutation>;
let produce: ReturnType<typeof mutation>;

function produced(
  events: string[],
  errors: unknown[] = []
): ProducedEventsInfo {
  return { events, errors, exhausted: false } as ProducedEventsInfo;
}

function setup(initialized?: boolean) {
  const onInitializedChange = vi.fn();
  const getPluginConfig = vi.fn(() => CONFIG);

  renderWithProviders(
    <ProjectNameProvider initialProjectName="web">
      <GetPluginConfigProvider getPluginConfig={getPluginConfig}>
        <DebuggerTab
          initialized={initialized}
          onInitializedChange={
            initialized === undefined ? undefined : onInitializedChange
          }
        />
      </GetPluginConfigProvider>
    </ProjectNameProvider>
  );

  return { onInitializedChange, getPluginConfig };
}

beforeEach(() => {
  vi.clearAllMocks();

  initialize = mutation();
  release = mutation();
  produce = mutation(produced(['{"a":1}']));

  vi.mocked(useInitializeEventPluginMutation).mockReturnValue(
    initialize as unknown as ReturnType<typeof useInitializeEventPluginMutation>
  );
  vi.mocked(useReleaseEventPluginMutation).mockReturnValue(
    release as unknown as ReturnType<typeof useReleaseEventPluginMutation>
  );
  vi.mocked(useProduceEventsMutation).mockReturnValue(
    produce as unknown as ReturnType<typeof useProduceEventsMutation>
  );
});

/**
 * The debugger produces events against a plugin instance that lives on
 * the backend for as long as the session does. Producing without one
 * fails, so the whole point of the state here is that producing is
 * closed off until the instance is confirmed - and opens up the moment
 * it is.
 */
describe('DebuggerTab', () => {
  it('starts stopped, with nothing produced', () => {
    setup();

    expect(screen.getByText('Stopped')).toBeInTheDocument();
    expect(
      screen.getByText(/Start the plugin instance, then produce events/)
    ).toBeInTheDocument();
  });

  it('offers no producing until an instance is running', () => {
    setup();

    expect(screen.getByRole('button', { name: /Produce/ })).toBeDisabled();
  });

  it('sends the configuration currently in the studio when starting', async () => {
    const user = userEvent.setup();
    const { getPluginConfig } = setup();

    await user.click(screen.getByRole('button', { name: /Start/ }));

    expect(getPluginConfig).toHaveBeenCalled();
    expect(initialize.mutate.mock.calls[0]?.[0]).toEqual({
      name: 'web',
      eventPluginConfig: CONFIG,
    });
  });

  it('reports the instance as running once it started', async () => {
    const user = userEvent.setup();
    setup();

    await user.click(screen.getByRole('button', { name: /Start/ }));

    expect(await screen.findByText('Running')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Produce/ })).toBeEnabled();
  });

  it('stays stopped when the instance could not be started', async () => {
    const user = userEvent.setup();
    initialize = mutation(undefined, true);
    vi.mocked(useInitializeEventPluginMutation).mockReturnValue(
      initialize as unknown as ReturnType<
        typeof useInitializeEventPluginMutation
      >
    );

    setup();

    await user.click(screen.getByRole('button', { name: /Start/ }));

    expect(screen.getByText('Stopped')).toBeInTheDocument();
  });

  it('produces events against the running instance', async () => {
    const user = userEvent.setup();
    setup();

    await user.click(screen.getByRole('button', { name: /Start/ }));
    await user.click(await screen.findByRole('button', { name: /Produce/ }));

    expect(produce.mutate).toHaveBeenCalledTimes(1);
    expect(await screen.findByText('Events')).toBeInTheDocument();
  });

  it('says so when the parameters produced nothing', async () => {
    const user = userEvent.setup();
    produce = mutation(produced([]));
    vi.mocked(useProduceEventsMutation).mockReturnValue(
      produce as unknown as ReturnType<typeof useProduceEventsMutation>
    );

    setup();

    await user.click(screen.getByRole('button', { name: /Start/ }));
    await user.click(await screen.findByRole('button', { name: /Produce/ }));

    expect(
      await screen.findByText('No events produced for these parameters.')
    ).toBeInTheDocument();
  });

  it('reports a failure against the event it happened on', async () => {
    const user = userEvent.setup();
    produce = mutation(
      produced([], [{ index: 0, message: 'boom', context: { reason: 'why' } }])
    );
    vi.mocked(useProduceEventsMutation).mockReturnValue(
      produce as unknown as ReturnType<typeof useProduceEventsMutation>
    );

    setup();

    await user.click(screen.getByRole('button', { name: /Start/ }));
    await user.click(await screen.findByRole('button', { name: /Produce/ }));

    expect(await screen.findByText(/At event #1: boom/)).toBeInTheDocument();
  });

  it('releases the instance when stopped', async () => {
    const user = userEvent.setup();
    setup();

    await user.click(screen.getByRole('button', { name: /Start/ }));
    await user.click(await screen.findByRole('button', { name: /Stop/ }));

    expect(release.mutate.mock.calls[0]?.[0]).toEqual({ name: 'web' });
    expect(screen.getByText('Stopped')).toBeInTheDocument();
  });

  /**
   * The console keeps the session across stage switches, so the state
   * may be owned by whoever mounted the tab rather than by the tab.
   */
  it('reports the state upwards when it is owned outside', async () => {
    const user = userEvent.setup();
    const { onInitializedChange } = setup(false);

    await user.click(screen.getByRole('button', { name: /Start/ }));

    expect(onInitializedChange).toHaveBeenCalledWith(true);
  });

  it('takes the state it is given rather than its own', () => {
    setup(true);

    expect(screen.getByText('Running')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Produce/ })).toBeEnabled();
  });
});
