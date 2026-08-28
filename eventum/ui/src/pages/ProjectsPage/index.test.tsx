import { ModalsProvider } from '@mantine/modals';
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import ProjectsPage from './index';
import * as configHooks from '@/api/hooks/useGeneratorConfigs';
import * as generatorHooks from '@/api/hooks/useGenerators';
import * as startupHooks from '@/api/hooks/useStartup';
import { GeneratorDirsExtendedInfo } from '@/api/routes/generator-configs/schemas';
import { renderWithProviders } from '@/test/render';

vi.mock('@/api/hooks/useGeneratorConfigs');
vi.mock('@/api/hooks/useGenerators');
vi.mock('@/api/hooks/useStartup');

const DIRS: GeneratorDirsExtendedInfo = [
  {
    name: 'web',
    size_in_bytes: 2048,
    last_modified: 1_755_000_000,
    generator_ids: ['web-prod'],
  },
  {
    name: 'db',
    size_in_bytes: 1024,
    last_modified: 1_755_000_100,
    generator_ids: [],
  },
];

const mutation = () => ({ mutate: vi.fn(), isPending: false });

function setup(dirs: GeneratorDirsExtendedInfo | null = DIRS, state = {}) {
  vi.mocked(configHooks.useGeneratorDirs).mockReturnValue({
    data: dirs ?? undefined,
    isLoading: false,
    isError: false,
    error: null,
    isSuccess: dirs !== null,
    ...state,
  } as unknown as ReturnType<typeof configHooks.useGeneratorDirs>);

  renderWithProviders(
    <MemoryRouter>
      <ModalsProvider>
        <ProjectsPage />
      </ModalsProvider>
    </MemoryRouter>
  );
}

function row(name: string) {
  return screen.getByRole('row', { name: new RegExp(name) });
}

beforeEach(() => {
  vi.clearAllMocks();

  for (const name of Object.keys(configHooks)) {
    if (name.startsWith('use') && name.endsWith('Mutation')) {
      vi.mocked(
        configHooks[name as keyof typeof configHooks] as () => unknown
      ).mockReturnValue(mutation());
    }
  }

  vi.mocked(generatorHooks.useGenerators).mockReturnValue({
    data: [],
  } as unknown as ReturnType<typeof generatorHooks.useGenerators>);

  for (const name of Object.keys(generatorHooks)) {
    if (name.endsWith('Mutation') || name === 'useUpdateGeneratorStatus') {
      vi.mocked(
        generatorHooks[name as keyof typeof generatorHooks] as () => unknown
      ).mockReturnValue(mutation());
    }
  }

  for (const name of Object.keys(startupHooks)) {
    if (name.endsWith('Mutation')) {
      vi.mocked(
        startupHooks[name as keyof typeof startupHooks] as () => unknown
      ).mockReturnValue(mutation());
    }
  }

  vi.mocked(startupHooks.useStartupGenerators).mockReturnValue({
    data: [],
  } as unknown as ReturnType<typeof startupHooks.useStartupGenerators>);
});

/**
 * The projects table is also the workspace inventory: which project
 * directories exist and which of them anything actually runs. The
 * "in use" reading is the part that carries information - an unused
 * project is one nothing would notice being broken.
 */
describe('ProjectsPage', () => {
  it('lists the project directories', () => {
    setup();

    expect(row('web')).toBeInTheDocument();
    expect(row('db')).toBeInTheDocument();
  });

  it('counts them and how many are in use', () => {
    setup();

    expect(screen.getByText(/2 projects/)).toBeInTheDocument();
    expect(screen.getByText(/1 in use/)).toBeInTheDocument();
  });

  it('names the instances a project is used by', () => {
    setup();

    expect(within(row('web')).getByText('web-prod')).toBeInTheDocument();
  });

  it('marks a project nothing uses', () => {
    setup();

    expect(within(row('db')).getByText('Not used')).toBeInTheDocument();
  });

  it('offers to create the first project when there are none', () => {
    setup([]);

    expect(screen.getByText('No projects yet')).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: 'Create new project' })
    ).toBeInTheDocument();
  });

  it('waits while the list is being read', () => {
    setup(null, { isLoading: true, isSuccess: false });

    expect(screen.queryByRole('table')).not.toBeInTheDocument();
  });

  it('reports a failure to read it', () => {
    setup(null, {
      isLoading: false,
      isSuccess: false,
      isError: true,
      error: new Error('no connection'),
    });

    expect(
      screen.getByText('Failed to load projects list')
    ).toBeInTheDocument();
    expect(screen.getByText(/no connection/)).toBeInTheDocument();
  });

  it('filters the list by project name', async () => {
    const user = userEvent.setup();
    setup();

    await user.type(screen.getByPlaceholderText('search by name...'), 'web');

    expect(screen.getByRole('row', { name: /web/ })).toBeInTheDocument();
    expect(screen.queryByRole('row', { name: /^db/ })).not.toBeInTheDocument();
  });

  it('filters the list down to the unused projects', async () => {
    const user = userEvent.setup();
    setup();

    await user.click(screen.getByRole('radio', { name: 'Unused' }));

    expect(screen.getByRole('row', { name: /db/ })).toBeInTheDocument();
    expect(
      screen.queryByRole('row', { name: /web-prod/ })
    ).not.toBeInTheDocument();
  });

  /**
   * Filtering by instance only means anything over projects that have
   * one, so it is closed off together with the unused filter.
   */
  it('stops offering the instance filter over unused projects', async () => {
    const user = userEvent.setup();
    setup();

    await user.click(screen.getByRole('radio', { name: 'Unused' }));

    expect(screen.getByPlaceholderText('search by instance')).toBeDisabled();
  });

  it('offers the create and import actions', () => {
    setup();

    expect(screen.getByRole('button', { name: 'Create new' })).toBeEnabled();
    expect(screen.getByRole('button', { name: 'Import' })).toBeEnabled();
  });

  it('opens the new project dialog', async () => {
    const user = userEvent.setup();
    setup();

    await user.click(screen.getByRole('button', { name: 'Create new' }));

    const dialog = await screen.findByRole('dialog');

    expect(dialog).toHaveTextContent('Template');
    expect(dialog).toHaveTextContent('Replay');
    expect(dialog).toHaveTextContent('Script');
  });
});
