import { ModalsProvider } from '@mantine/modals';
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import ScenariosPage from './index';
import * as generatorHooks from '@/api/hooks/useGenerators';
import * as scenarioHooks from '@/api/hooks/useScenarios';
import * as startupHooks from '@/api/hooks/useStartup';
import { GeneratorsInfo } from '@/api/routes/generators/schemas';
import { StartupGeneratorParametersList } from '@/api/routes/startup/schemas';
import { renderWithProviders } from '@/test/render';

vi.mock('@/api/hooks/useGenerators');
vi.mock('@/api/hooks/useScenarios');
vi.mock('@/api/hooks/useStartup');

const IDLE = {
  is_initializing: false,
  is_running: false,
  is_ended_up: false,
  is_ended_up_successfully: false,
  is_stopping: false,
};

const STARTUP: StartupGeneratorParametersList = [
  { id: 'web', path: '/p/web', scenarios: ['corp'] },
  { id: 'db', path: '/p/db', scenarios: ['corp', 'lab'] },
  { id: 'idle', path: '/p/idle', scenarios: [] },
];

const GENERATORS: GeneratorsInfo = [
  {
    id: 'web',
    path: '/p/web',
    status: { ...IDLE, is_running: true },
    start_time: null,
  },
  { id: 'db', path: '/p/db', status: IDLE, start_time: null },
  { id: 'idle', path: '/p/idle', status: IDLE, start_time: null },
];

const mutation = () => ({ mutate: vi.fn(), isPending: false });

let bulkStart: ReturnType<typeof mutation>;
let bulkStop: ReturnType<typeof mutation>;
let deleteScenario: ReturnType<typeof mutation>;

function setup(
  startup: StartupGeneratorParametersList | null = STARTUP,
  generators: GeneratorsInfo | null = GENERATORS,
  state: Record<string, unknown> = {}
) {
  vi.mocked(startupHooks.useStartupGenerators).mockReturnValue({
    data: startup ?? undefined,
    isLoading: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
    ...state,
  } as unknown as ReturnType<typeof startupHooks.useStartupGenerators>);

  vi.mocked(generatorHooks.useGenerators).mockReturnValue({
    data: generators ?? undefined,
    isLoading: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
    ...state,
  } as unknown as ReturnType<typeof generatorHooks.useGenerators>);

  renderWithProviders(
    <MemoryRouter>
      <ModalsProvider>
        <ScenariosPage />
      </ModalsProvider>
    </MemoryRouter>
  );
}

function row(name: string) {
  return screen.getByRole('row', { name: new RegExp(name) });
}

beforeEach(() => {
  vi.clearAllMocks();

  bulkStart = mutation();
  bulkStop = mutation();
  deleteScenario = mutation();

  vi.mocked(generatorHooks.useBulkStartGeneratorMutation).mockReturnValue(
    bulkStart as never
  );
  vi.mocked(generatorHooks.useBulkStopGeneratorMutation).mockReturnValue(
    bulkStop as never
  );
  vi.mocked(generatorHooks.useUpdateGeneratorStatus).mockReturnValue(
    mutation() as never
  );
  vi.mocked(scenarioHooks.useDeleteScenarioMutation).mockReturnValue(
    deleteScenario as never
  );
});

/**
 * A scenario is not stored anywhere of its own: it exists because
 * startup entries name it. The page therefore derives the list, and
 * what it derives has to hold - an instance that belongs to two
 * scenarios counts in both, and one that belongs to none appears in
 * neither.
 */
describe('ScenariosPage', () => {
  it('derives the scenarios the startup entries name', () => {
    setup();

    expect(row('corp')).toBeInTheDocument();
    expect(row('lab')).toBeInTheDocument();
  });

  it('leaves out an instance that belongs to no scenario', () => {
    setup();

    expect(screen.queryByRole('row', { name: /idle/ })).not.toBeInTheDocument();
  });

  it('counts an instance in every scenario it belongs to', () => {
    setup();

    expect(within(row('corp')).getByText('web')).toBeInTheDocument();
    expect(within(row('corp')).getByText('db')).toBeInTheDocument();
    expect(within(row('lab')).getByText('db')).toBeInTheDocument();
  });

  it('counts the scenarios and how many are active', () => {
    setup();

    expect(screen.getByText(/2 scenarios/)).toBeInTheDocument();
    expect(screen.getAllByText(/1 active/).length).toBeGreaterThan(0);
  });

  it('orders the scenarios by name', () => {
    setup();

    const names = screen
      .getAllByRole('row')
      .slice(1)
      .map((element) => element.textContent ?? '');

    expect(names[0]).toContain('corp');
    expect(names[1]).toContain('lab');
  });

  it('offers to create the first scenario when there are none', () => {
    setup([{ id: 'web', path: '/p/web', scenarios: [] }]);

    expect(screen.getByText('No scenarios yet')).toBeInTheDocument();
  });

  it('waits while either list is being read', () => {
    setup(null, null, { isLoading: true });

    expect(screen.queryByRole('table')).not.toBeInTheDocument();
  });

  it('reports a failure to read them', () => {
    setup(null, null, {
      isLoading: false,
      isError: true,
      error: new Error('no connection'),
    });

    expect(screen.getByText('Failed to load scenarios')).toBeInTheDocument();
  });

  it('filters the list by name', async () => {
    const user = userEvent.setup();
    setup();

    await user.type(screen.getByPlaceholderText('search by name...'), 'lab');

    expect(screen.getByRole('row', { name: /lab/ })).toBeInTheDocument();
    expect(screen.queryByRole('row', { name: /corp/ })).not.toBeInTheDocument();
  });

  it('filters the list down to the running scenarios', async () => {
    const user = userEvent.setup();
    setup();

    await user.click(screen.getByRole('radio', { name: 'Running' }));

    expect(screen.getByRole('row', { name: /corp/ })).toBeInTheDocument();
    expect(screen.queryByRole('row', { name: /lab/ })).not.toBeInTheDocument();
  });

  it('offers no bulk action until a scenario is selected', () => {
    setup();

    for (const name of ['Start selected', 'Stop selected', 'Delete selected']) {
      expect(screen.getByRole('button', { name })).toBeDisabled();
    }
  });

  it('starts every instance of the selected scenarios', async () => {
    const user = userEvent.setup();
    setup();

    await user.click(within(row('lab')).getByRole('checkbox'));
    await user.click(screen.getByRole('button', { name: 'Start selected' }));

    expect(bulkStart.mutate).toHaveBeenCalledTimes(1);
    expect(bulkStart.mutate.mock.calls[0]?.[0]).toMatchObject({ ids: ['db'] });
  });
});
