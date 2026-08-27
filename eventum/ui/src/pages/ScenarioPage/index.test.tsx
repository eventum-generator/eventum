import { ModalsProvider } from '@mantine/modals';
import { screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import ScenarioPage from './index';
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
  { id: 'web', path: '/p/web', scenarios: ['corp net'] },
  { id: 'db', path: '/p/db', scenarios: ['corp net'] },
  { id: 'elsewhere', path: '/p/elsewhere', scenarios: ['lab'] },
];

const GENERATORS: GeneratorsInfo = [
  {
    id: 'web',
    path: '/p/web',
    status: { ...IDLE, is_running: true },
    start_time: null,
  },
  { id: 'db', path: '/p/db', status: IDLE, start_time: null },
];

const mutation = () => ({ mutate: vi.fn(), isPending: false });

function setup(
  name = 'corp%20net',
  state: Record<string, unknown> = {},
  startup: StartupGeneratorParametersList | null = STARTUP
) {
  vi.mocked(startupHooks.useStartupGenerators).mockReturnValue({
    data: startup ?? undefined,
    isLoading: false,
    isError: false,
    error: null,
    ...state,
  } as unknown as ReturnType<typeof startupHooks.useStartupGenerators>);

  vi.mocked(generatorHooks.useGenerators).mockReturnValue({
    data: GENERATORS,
    isLoading: false,
    isError: false,
    error: null,
    ...state,
  } as unknown as ReturnType<typeof generatorHooks.useGenerators>);

  renderWithProviders(
    <MemoryRouter initialEntries={[`/scenarios/${name}`]}>
      <ModalsProvider>
        <Routes>
          <Route path="/scenarios/:scenarioName" element={<ScenarioPage />} />
        </Routes>
      </ModalsProvider>
    </MemoryRouter>
  );
}

beforeEach(() => {
  vi.clearAllMocks();

  vi.mocked(scenarioHooks.useMultiGlobalsUsage).mockReturnValue(
    [] as unknown as ReturnType<typeof scenarioHooks.useMultiGlobalsUsage>
  );
  vi.mocked(scenarioHooks.useScenarioGlobalState).mockReturnValue({
    data: {},
    isLoading: false,
    isError: false,
    isSuccess: true,
    error: null,
    refetch: vi.fn(),
  } as unknown as ReturnType<typeof scenarioHooks.useScenarioGlobalState>);

  for (const module of [scenarioHooks, generatorHooks, startupHooks]) {
    for (const name of Object.keys(module)) {
      if (name.endsWith('Mutation') || name === 'useUpdateGeneratorStatus') {
        vi.mocked(
          module[name as keyof typeof module] as () => unknown
        ).mockReturnValue(mutation());
      }
    }
  }
});

/**
 * A scenario page is opened by name, and the name comes from the URL -
 * where a space or a slash arrives escaped. Reading it back wrong shows
 * an empty scenario for one that exists, which is the failure this
 * page is most exposed to.
 */
describe('ScenarioPage', () => {
  it('names the scenario the address points at', () => {
    setup();

    expect(
      screen.getByRole('heading', { name: 'corp net' })
    ).toBeInTheDocument();
  });

  it('shows only the instances that belong to it', () => {
    setup();

    expect(screen.getAllByText('web').length).toBeGreaterThan(0);
    expect(screen.getAllByText('db').length).toBeGreaterThan(0);
    expect(screen.queryByText('elsewhere')).not.toBeInTheDocument();
  });

  it('counts the instances it holds, and how many run', () => {
    setup();

    // The count is one line: "2 instances · 1 running".
    expect(
      screen.getAllByText((_content, element) =>
        /^2 instances .* 1 running$/.test(element?.textContent ?? '')
      ).length
    ).toBeGreaterThan(0);
  });

  it('links back to the scenario list', () => {
    setup();

    expect(
      screen.getByRole('link', { name: 'Back to scenarios' })
    ).toHaveAttribute('href', '/scenarios');
  });

  it('waits while either list is being read', () => {
    setup('corp%20net', { isLoading: true });

    expect(screen.queryByRole('heading', { name: 'corp net' })).toBeNull();
  });

  it('reports a failure to read them', () => {
    setup('corp%20net', {
      isLoading: false,
      isError: true,
      error: new Error('no connection'),
    });

    expect(screen.getByText('Failed to load scenario')).toBeInTheDocument();
    expect(screen.getByText(/no connection/)).toBeInTheDocument();
  });

  it('opens a scenario nothing belongs to without failing', () => {
    setup('empty');

    expect(screen.getByRole('heading', { name: 'empty' })).toBeInTheDocument();
    expect(screen.queryByText('web')).not.toBeInTheDocument();
  });

  it('opens without any startup entry read yet', () => {
    setup('corp%20net', {}, []);

    expect(
      screen.getByRole('heading', { name: 'corp net' })
    ).toBeInTheDocument();
  });
});
