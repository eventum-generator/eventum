import { ModalsProvider } from '@mantine/modals';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { RouterProvider, createMemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useInstanceHistory } from './dashboard/useInstanceHistory';
import InstancePage from './index';
import * as generators from '@/api/hooks/useGenerators';
import * as scenarios from '@/api/hooks/useScenarios';
import * as startup from '@/api/hooks/useStartup';
import {
  GeneratorParameters,
  GeneratorStatus,
} from '@/api/routes/generators/schemas';
import { StartupGeneratorParameters } from '@/api/routes/startup/schemas';
import { renderWithProviders } from '@/test/render';

vi.mock('@/api/hooks/useGenerators');
vi.mock('@/api/hooks/useScenarios');
vi.mock('@/api/hooks/useStartup');
vi.mock('./dashboard/useInstanceHistory');

const IDLE: GeneratorStatus = {
  is_initializing: false,
  is_running: false,
  is_ended_up: false,
  is_ended_up_successfully: false,
  is_stopping: false,
};

const PARAMS = {
  id: 'web',
  path: 'web/generator.yml',
  live_mode: true,
  skip_past: true,
} as GeneratorParameters;

const STARTUP_PARAMS = {
  ...PARAMS,
  autostart: false,
  scenarios: [],
} as StartupGeneratorParameters;

interface Options {
  isLoading?: boolean;
  paramsError?: boolean;
  startupError?: boolean;
  statusError?: boolean;
  status?: GeneratorStatus;
}

function query(data: unknown, options: Options, failing: boolean) {
  return {
    data: failing ? undefined : data,
    isLoading: options.isLoading ?? false,
    isError: failing,
    isSuccess: options.isLoading !== true && !failing,
    error: failing ? new Error('unreachable') : null,
  } as never;
}

function setup(options: Options = {}) {
  vi.mocked(generators.useGeneratorStatus).mockReturnValue(
    query(options.status ?? IDLE, options, options.statusError === true)
  );
  vi.mocked(generators.useGenerator).mockReturnValue(
    query(PARAMS, options, options.paramsError === true)
  );
  vi.mocked(startup.useStartupGenerator).mockReturnValue(
    query(STARTUP_PARAMS, options, options.startupError === true)
  );
  // The page reads the names of every scenario as a list.
  vi.mocked(scenarios.useScenarios).mockReturnValue({
    data: ['nightly'],
  } as never);

  const idle = { mutate: vi.fn(), isPending: false } as never;

  vi.mocked(generators.useUpdateGeneratorMutation).mockReturnValue(idle);
  vi.mocked(generators.useStopGeneratorMutation).mockReturnValue(idle);
  vi.mocked(generators.useStartGeneratorMutation).mockReturnValue(idle);
  vi.mocked(generators.useUpdateGeneratorStatus).mockReturnValue(idle);
  vi.mocked(generators.useGenerators).mockReturnValue({
    data: [
      { id: 'web', path: 'web/generator.yml', status: IDLE, start_time: null },
    ],
  } as never);
  vi.mocked(startup.useUpdateGeneratorInStartupMutation).mockReturnValue(idle);
  vi.mocked(scenarios.useAddGeneratorToScenarioMutation).mockReturnValue(idle);
  vi.mocked(scenarios.useRemoveGeneratorFromScenarioMutation).mockReturnValue(
    idle
  );
  vi.mocked(useInstanceHistory).mockReturnValue({
    stats: undefined,
    flow: [],
    inputEps: 0,
    outputEps: 0,
    cpuPercent: 0,
  });

  const router = createMemoryRouter(
    [{ path: '/instances/:instanceId', element: <InstancePage /> }],
    { initialEntries: ['/instances/web'] }
  );

  renderWithProviders(
    <ModalsProvider>
      <RouterProvider router={router} />
    </ModalsProvider>
  );

  return { user: userEvent.setup() };
}

beforeEach(() => {
  vi.clearAllMocks();
});

/**
 * The page of one instance reads three things that can each fail on
 * their own - what it runs, how it is registered at startup, and what it
 * is doing right now - and it cannot draw a form over any of them
 * missing: the form would then save defaults over the real settings.
 */
describe('InstancePage', () => {
  it('opens on the instance of the address', () => {
    setup();

    expect(screen.getByRole('heading', { name: 'web' })).toBeVisible();
  });

  it('offers its three views', () => {
    setup();

    for (const tab of ['Overview', 'Settings', 'Logs']) {
      expect(screen.getByRole('tab', { name: tab })).toBeVisible();
    }
  });

  it('opens on the overview', () => {
    setup();

    expect(screen.getByRole('tab', { name: 'Overview' })).toHaveAttribute(
      'aria-selected',
      'true'
    );
  });

  it('switches to the view that was picked', async () => {
    const { user } = setup();

    await user.click(screen.getByRole('tab', { name: 'Settings' }));

    expect(screen.getByRole('tab', { name: 'Settings' })).toHaveAttribute(
      'aria-selected',
      'true'
    );
    expect(screen.getByText('Emission mode')).toBeVisible();
  });

  it('waits rather than drawing a form over what it has not read', () => {
    setup({ isLoading: true });

    expect(screen.queryByRole('tab', { name: 'Settings' })).toBeNull();
  });

  it.each([
    [
      'what the instance runs',
      'paramsError',
      'Failed to get instance parameters',
    ],
    [
      'how it is registered',
      'startupError',
      'Failed to get startup instance parameters',
    ],
    ['what it is doing', 'statusError', 'Failed to get instance status'],
  ])('reports a failure to read %s', (_label, key, title) => {
    setup({ [key]: true });

    expect(screen.getByText(title)).toBeVisible();
    expect(screen.queryByRole('tab', { name: 'Settings' })).toBeNull();
  });

  it('offers no save until something is edited', () => {
    setup();

    expect(screen.queryByRole('button', { name: 'Save' })).toBeNull();
  });

  it('offers a save once a setting is edited', async () => {
    const { user } = setup();

    await user.click(screen.getByRole('tab', { name: 'Settings' }));

    const autostart = screen.getByRole('switch', { name: 'Autostart' });
    autostart.focus();
    await user.keyboard(' ');

    expect(screen.getByRole('button', { name: 'Save' })).toBeVisible();
  });
});
