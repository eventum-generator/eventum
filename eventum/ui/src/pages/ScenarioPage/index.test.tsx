import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { RouterProvider, createMemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import ScenarioPage from './index';
import * as generators from '@/api/hooks/useGenerators';
import * as scenarios from '@/api/hooks/useScenarios';
import { useStartupGenerators } from '@/api/hooks/useStartup';
import { GeneratorStatus } from '@/api/routes/generators/schemas';
import { StartupGeneratorParameters } from '@/api/routes/startup/schemas';
import { renderWithProviders } from '@/test/render';

vi.mock('@/api/hooks/useGenerators');
vi.mock('@/api/hooks/useScenarios');
vi.mock('@/api/hooks/useStartup');

const IDLE: GeneratorStatus = {
  is_initializing: false,
  is_running: false,
  is_ended_up: false,
  is_ended_up_successfully: false,
  is_stopping: false,
};

const RUNNING: GeneratorStatus = { ...IDLE, is_running: true };

function member(
  id: string,
  scenarioNames: string[] = ['nightly']
): StartupGeneratorParameters {
  return {
    id,
    path: `${id}/generator.yml`,
    scenarios: scenarioNames,
  } as StartupGeneratorParameters;
}

const bulkStart = { mutate: vi.fn(), isPending: false };
const bulkStop = { mutate: vi.fn(), isPending: false };

interface Options {
  entries?: StartupGeneratorParameters[];
  statuses?: [string, GeneratorStatus][];
  isLoading?: boolean;
  isError?: boolean;
}

function setup(options: Options = {}) {
  vi.mocked(useStartupGenerators).mockReturnValue({
    data: options.entries ?? [member('web')],
    isLoading: options.isLoading ?? false,
    isError: options.isError ?? false,
    isSuccess: options.isLoading !== true && options.isError !== true,
    error: options.isError === true ? new Error('no startup') : null,
  } as unknown as ReturnType<typeof useStartupGenerators>);

  vi.mocked(generators.useGenerators).mockReturnValue({
    data: (options.entries ?? [member('web')]).map((entry) => ({
      id: entry.id,
      path: entry.path,
      status: new Map(options.statuses ?? []).get(entry.id) ?? IDLE,
      start_time: null,
    })),
    isLoading: options.isLoading ?? false,
    isError: options.isError ?? false,
    isSuccess: options.isLoading !== true && options.isError !== true,
    error: options.isError === true ? new Error('no generators') : null,
  } as unknown as ReturnType<typeof generators.useGenerators>);

  vi.mocked(generators.useBulkStartGeneratorMutation).mockReturnValue(
    bulkStart as never
  );
  vi.mocked(generators.useBulkStopGeneratorMutation).mockReturnValue(
    bulkStop as never
  );
  vi.mocked(generators.useUpdateGeneratorStatus).mockReturnValue({
    mutate: vi.fn(),
  } as never);
  vi.mocked(scenarios.useMultiGlobalsUsage).mockReturnValue([] as never);
  vi.mocked(scenarios.useScenarios).mockReturnValue({
    data: { nightly: ['web'] },
  } as never);
  vi.mocked(scenarios.useRemoveGeneratorFromScenarioMutation).mockReturnValue({
    mutate: vi.fn(),
  } as never);
  vi.mocked(scenarios.useAddGeneratorToScenarioMutation).mockReturnValue({
    mutate: vi.fn(),
  } as never);

  // The page mounts a card per instance and the global-state panel, and
  // each of those reaches for mutations of its own.
  const idle = { mutate: vi.fn(), isPending: false } as never;

  vi.mocked(generators.useStartGeneratorMutation).mockReturnValue(idle);
  vi.mocked(generators.useStopGeneratorMutation).mockReturnValue(idle);
  vi.mocked(scenarios.useUpdateScenarioGlobalStateMutation).mockReturnValue(
    idle
  );
  vi.mocked(scenarios.useClearScenarioGlobalStateMutation).mockReturnValue(
    idle
  );
  vi.mocked(scenarios.useDeleteScenarioGlobalStateKeyMutation).mockReturnValue(
    idle
  );
  vi.mocked(scenarios.useScenarioGlobalState).mockReturnValue({
    data: {},
    isLoading: false,
    isError: false,
    isSuccess: true,
    error: null,
    refetch: vi.fn(),
  } as never);

  const router = createMemoryRouter(
    [{ path: '/scenarios/:scenarioName', element: <ScenarioPage /> }],
    { initialEntries: ['/scenarios/nightly'] }
  );

  renderWithProviders(<RouterProvider router={router} />);

  return { user: userEvent.setup() };
}

beforeEach(() => {
  vi.clearAllMocks();
});

/**
 * The page of one scenario is the set it groups and the two actions that
 * act on all of it. Membership is not stored on the scenario but on each
 * instance, so the set is whatever names this scenario - and an action
 * only makes sense while something in the set can take it.
 */
describe('ScenarioPage', () => {
  it('names the scenario it opened', () => {
    setup();

    expect(screen.getByRole('heading', { name: 'nightly' })).toBeVisible();
  });

  it('lists the instances that name this scenario', () => {
    setup({
      entries: [member('web'), member('api'), member('other', ['smoke'])],
    });

    // Each instance is named on its card and again as the project it
    // runs, so what matters is that it is there at all - and that the
    // one naming another scenario is not.
    expect(screen.getAllByText('web').length).toBeGreaterThan(0);
    expect(screen.getAllByText('api').length).toBeGreaterThan(0);
    expect(screen.queryByText('other')).toBeNull();
  });

  it('offers a start while something in it is at rest', () => {
    setup({ statuses: [['web', IDLE]] });

    expect(screen.getByRole('button', { name: 'Start all' })).toBeEnabled();
    expect(screen.getByRole('button', { name: 'Stop all' })).toBeDisabled();
  });

  it('offers a stop once something in it runs', () => {
    setup({ statuses: [['web', RUNNING]] });

    expect(screen.getByRole('button', { name: 'Stop all' })).toBeEnabled();
    expect(screen.getByRole('button', { name: 'Start all' })).toBeDisabled();
  });

  it('starts the whole set at once', async () => {
    const { user } = setup({ statuses: [['web', IDLE]] });

    await user.click(screen.getByRole('button', { name: 'Start all' }));

    expect(bulkStart.mutate).toHaveBeenCalledWith(
      { ids: ['web'] },
      expect.anything()
    );
  });

  it('stops the whole set at once', async () => {
    const { user } = setup({ statuses: [['web', RUNNING]] });

    await user.click(screen.getByRole('button', { name: 'Stop all' }));

    expect(bulkStop.mutate).toHaveBeenCalledWith(
      { ids: ['web'] },
      expect.anything()
    );
  });

  it('asks for an instance rather than drawing an empty set', () => {
    setup({ entries: [member('web', ['smoke'])] });

    // No instance names this scenario, so there is nothing to act on
    // and the two bulk actions are not offered at all.
    expect(screen.queryByRole('button', { name: 'Start all' })).toBeNull();
  });

  it('waits rather than drawing a set it has not read', () => {
    setup({ isLoading: true });

    expect(screen.queryByRole('button', { name: 'Start all' })).toBeNull();
  });

  it('reports what it could not read', () => {
    setup({ isError: true });

    expect(screen.getByText('Failed to load scenario')).toBeInTheDocument();
  });
});
