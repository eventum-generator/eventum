import { ModalsProvider } from '@mantine/modals';
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { RepositoryCatalog } from './RepositoryCatalog';
import {
  useInstallGeneratorMutation,
  useRepositoryCatalog,
} from '@/api/hooks/useRepositories';
import {
  Catalog,
  CatalogEntry,
  ConnectedRepository,
} from '@/api/routes/repositories/schemas';
import { renderWithProviders } from '@/test/render';

vi.mock('@/api/hooks/useRepositories');

const REPOSITORY = {
  name: 'content-packs',
  url: 'https://example.com/repo.git',
  status: { state: 'available', checked_at: null, reason: null },
} as ConnectedRepository;

function entry(overrides: Partial<CatalogEntry> = {}): CatalogEntry {
  return {
    name: 'web-nginx',
    path: 'generators/web-nginx',
    title: 'Nginx access log',
    summary: 'Access and error events of an nginx server',
    file_count: 7,
    size: 20_480,
    installed_as: [],
    ...overrides,
  } as CatalogEntry;
}

function catalog(entries: CatalogEntry[]): Catalog {
  return {
    revision: 'a1b2c3d4e5f6',
    refreshed_at: '2026-08-01T10:00:00+00:00',
    committed_at: '2026-07-31T09:00:00+00:00',
    author: 'Eventum Team',
    entries,
  } as Catalog;
}

interface Options {
  data?: Catalog;
  isLoading?: boolean;
  isError?: boolean;
  enabled?: boolean;
}

function setup(options: Options = {}) {
  vi.mocked(useInstallGeneratorMutation).mockReturnValue({
    mutate: vi.fn(),
    isPending: false,
  } as never);
  vi.mocked(useRepositoryCatalog).mockReturnValue({
    data: options.data,
    isLoading: options.isLoading ?? false,
    isError: options.isError ?? false,
    error: options.isError === true ? new Error('unreachable') : null,
    isSuccess: options.data !== undefined,
  } as unknown as ReturnType<typeof useRepositoryCatalog>);

  renderWithProviders(
    <MemoryRouter>
      <ModalsProvider>
        <RepositoryCatalog
          repository={REPOSITORY}
          existingProjectNames={['web']}
          enabled={options.enabled ?? true}
        />
      </ModalsProvider>
    </MemoryRouter>
  );

  return userEvent.setup();
}

beforeEach(() => {
  vi.clearAllMocks();
});

/**
 * The catalog of a repository is what a user installs from, and reading
 * it makes the instance fetch that repository - so it is read only for
 * the repository that is open. A generator already installed as a
 * project is not offered again: what it offers instead is the project,
 * or an update when the installed copy is behind.
 */
describe('RepositoryCatalog', () => {
  it('lists what the repository publishes', () => {
    setup({ data: catalog([entry()]) });

    expect(screen.getByText('web-nginx')).toBeInTheDocument();
    expect(screen.getByText('Nginx access log')).toBeInTheDocument();
    expect(screen.getByText(/1 generator/)).toBeInTheDocument();
  });

  it('names the revision the listing was read at', () => {
    setup({ data: catalog([entry()]) });

    // Seven characters of it, the way a commit is named.
    expect(screen.getByText(/revision a1b2c3d/)).toBeInTheDocument();
    expect(screen.getByText(/by Eventum Team/)).toBeInTheDocument();
  });

  it('says a repository publishes nothing rather than drawing an empty table', () => {
    setup({ data: catalog([]) });

    expect(
      screen.getByText('The repository publishes no generators.')
    ).toBeInTheDocument();
  });

  it('reports a catalog it could not read', () => {
    setup({ isError: true });

    expect(screen.getByText('Failed to read the catalog')).toBeInTheDocument();
  });

  it('offers a generator to install', () => {
    setup({ data: catalog([entry()]) });

    expect(screen.getByRole('button', { name: 'Install' })).toBeInTheDocument();
  });

  it('offers the project instead of a second install', () => {
    setup({
      data: catalog([
        entry({
          installed_as: [
            {
              project: 'web',
              revision: 'a1b2c3d4e5f6',
              installed_at: '2026-08-01T10:00:00+00:00',
              outdated: false,
            },
          ],
        }),
      ]),
    });

    expect(screen.getByRole('button', { name: 'Open' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Install' })).toBeNull();
  });

  it('says an installed copy is behind the repository', () => {
    setup({
      data: catalog([
        entry({
          installed_as: [
            {
              project: 'web',
              revision: 'older',
              installed_at: '2026-07-01T10:00:00+00:00',
              outdated: true,
            },
          ],
        }),
      ]),
    });

    expect(screen.getByText(/Update available/i)).toBeInTheDocument();
  });

  it('narrows the listing to what the search asks for', async () => {
    const user = setup({
      data: catalog([
        entry(),
        entry({ name: 'linux-auditd', title: 'Auditd', summary: 'syscalls' }),
      ]),
    });

    await user.type(
      screen.getByPlaceholderText('search generators...'),
      'auditd'
    );

    expect(screen.getByText('linux-auditd')).toBeInTheDocument();
    expect(screen.queryByText('web-nginx')).toBeNull();
    expect(screen.getByText(/1 shown/)).toBeInTheDocument();
  });

  it('searches what a generator says about itself, not its name alone', async () => {
    const user = setup({ data: catalog([entry()]) });

    await user.type(
      screen.getByPlaceholderText('search generators...'),
      'nginx server'
    );

    expect(screen.getByText('web-nginx')).toBeInTheDocument();
  });

  it('says so when the search matches nothing', async () => {
    const user = setup({ data: catalog([entry()]) });

    await user.type(
      screen.getByPlaceholderText('search generators...'),
      'nothing'
    );

    expect(
      screen.getByText('No generator matches "nothing".')
    ).toBeInTheDocument();
  });

  it('reads the catalog only for the repository that is open', () => {
    setup({ enabled: false });

    // Reading it makes the instance fetch the repository, so a closed
    // row must not.
    expect(vi.mocked(useRepositoryCatalog)).toHaveBeenCalledWith(
      'content-packs',
      false
    );
  });

  it('opens the form of the generator that is being installed', async () => {
    const user = setup({ data: catalog([entry()]) });

    await user.click(screen.getByRole('button', { name: 'Install' }));

    const dialog = await screen.findByRole('dialog');
    expect(within(dialog).getByText('Install generator')).toBeInTheDocument();
  });
});
