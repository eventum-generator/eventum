import { ModalsProvider } from '@mantine/modals';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

import RepositoriesPage from './index';
import { listGeneratorDirs } from '@/api/routes/generator-configs';
import {
  checkRepository,
  getCatalog,
  getRepositories,
} from '@/api/routes/repositories';
import {
  Catalog,
  ConnectedRepository,
} from '@/api/routes/repositories/schemas';
import { renderWithProviders } from '@/test/render';

vi.mock('@/api/routes/repositories', () => ({
  getRepositories: vi.fn(),
  getCatalog: vi.fn(),
  refreshCatalog: vi.fn(),
  addRepository: vi.fn(),
  deleteRepository: vi.fn(),
  checkRepository: vi.fn(),
  installGenerator: vi.fn(),
}));

vi.mock('@/api/routes/generator-configs', () => ({
  listGeneratorDirs: vi.fn(),
}));

const getRepositoriesMock = vi.mocked(getRepositories);
const getCatalogMock = vi.mocked(getCatalog);
const checkRepositoryMock = vi.mocked(checkRepository);
const listGeneratorDirsMock = vi.mocked(listGeneratorDirs);

const REPOSITORY: ConnectedRepository = {
  name: 'packs',
  url: 'https://github.com/eventum-generator/content-packs.git',
  ref: 'master',
  status: { state: 'available', checked_at: '2026-08-19T10:00:00Z' },
};

const ENTRY = {
  name: 'web-nginx',
  path: 'generators/web-nginx',
  tree: 'b'.repeat(40),
  title: 'Nginx Access Logs',
  summary: 'Produces nginx access log entries.',
  file_count: 3,
  size: 2048,
  installed_as: [],
};

const CATALOG: Catalog = {
  revision: 'a'.repeat(40),
  refreshed_at: '2026-08-19T10:00:00Z',
  committed_at: '2026-08-18T10:00:00Z',
  author: 'Tester',
  entries: [
    ENTRY,
    {
      ...ENTRY,
      name: 'linux-auditd',
      path: 'generators/linux-auditd',
      title: 'Linux Auditd',
      summary: 'Produces auditd records.',
    },
  ],
};

function renderPage() {
  // The application mounts ModalsProvider above the router, so modal
  // content renders outside it - the order is mirrored here, or a
  // modal reaching for the router would pass in a test and fail in
  // the application.
  return renderWithProviders(
    <ModalsProvider>
      <MemoryRouter>
        <RepositoriesPage />
      </MemoryRouter>
    </ModalsProvider>
  );
}

async function openRepository() {
  await userEvent.click(await screen.findByText('packs'));
}

afterEach(() => {
  vi.clearAllMocks();
});

describe('RepositoriesPage', () => {
  it('offers to connect the first repository', async () => {
    getRepositoriesMock.mockResolvedValue([]);
    listGeneratorDirsMock.mockResolvedValue([]);

    renderPage();

    expect(
      await screen.findByText('No repositories connected')
    ).toBeInTheDocument();
  });

  it('lists connected repositories without reading their catalogs', async () => {
    getRepositoriesMock.mockResolvedValue([REPOSITORY]);
    listGeneratorDirsMock.mockResolvedValue([]);

    renderPage();

    expect(await screen.findByText('packs')).toBeInTheDocument();
    expect(await screen.findByText('Reachable')).toBeInTheDocument();
    expect(getCatalogMock).not.toHaveBeenCalled();
  });

  it('checks a repository whose state is not known yet', async () => {
    getRepositoriesMock.mockResolvedValue([
      { ...REPOSITORY, status: { state: 'unknown' } },
    ]);
    listGeneratorDirsMock.mockResolvedValue([]);
    checkRepositoryMock.mockResolvedValue({ state: 'available' });

    renderPage();

    await waitFor(() =>
      expect(checkRepositoryMock).toHaveBeenCalledWith('packs')
    );
  });

  it('reports a repository that did not answer', async () => {
    getRepositoriesMock.mockResolvedValue([
      {
        ...REPOSITORY,
        status: {
          state: 'unavailable',
          checked_at: '2026-08-19T10:00:00Z',
          reason: 'Connection refused',
        },
      },
    ]);
    listGeneratorDirsMock.mockResolvedValue([]);

    renderPage();

    expect(await screen.findByText('Unreachable')).toBeInTheDocument();
    expect(checkRepositoryMock).not.toHaveBeenCalled();
  });

  it('reads the catalog when a repository is opened', async () => {
    getRepositoriesMock.mockResolvedValue([REPOSITORY]);
    listGeneratorDirsMock.mockResolvedValue([]);
    getCatalogMock.mockResolvedValue(CATALOG);

    renderPage();
    await openRepository();

    expect(await screen.findByText('Nginx Access Logs')).toBeInTheDocument();
    await waitFor(() => expect(getCatalogMock).toHaveBeenCalledWith('packs'));
  });

  it('narrows the catalog to what the search matches', async () => {
    getRepositoriesMock.mockResolvedValue([REPOSITORY]);
    listGeneratorDirsMock.mockResolvedValue([]);
    getCatalogMock.mockResolvedValue(CATALOG);

    renderPage();
    await openRepository();
    await screen.findByText('Nginx Access Logs');

    await userEvent.type(
      screen.getByPlaceholderText('search generators...'),
      'auditd'
    );

    expect(screen.queryByText('Nginx Access Logs')).not.toBeInTheDocument();
    expect(screen.getByText('Linux Auditd')).toBeInTheDocument();
    expect(screen.getByText(/2 generators/)).toBeInTheDocument();
  });

  it('names the action of a generator already installed', async () => {
    getRepositoriesMock.mockResolvedValue([REPOSITORY]);
    listGeneratorDirsMock.mockResolvedValue(['nginx']);
    getCatalogMock.mockResolvedValue({
      ...CATALOG,
      entries: [
        {
          ...ENTRY,
          installed_as: [
            {
              project: 'nginx',
              revision: 'a'.repeat(40),
              installed_at: '2026-08-19T10:00:00Z',
              outdated: false,
            },
          ],
        },
      ],
    });

    renderPage();
    await openRepository();

    // What the workspace already holds is stated by the action, so
    // nothing repeats it beside the name.
    expect(await screen.findByText('Install again')).toBeInTheDocument();
    expect(screen.queryByText('installed')).not.toBeInTheDocument();
    expect(screen.queryByText('update available')).not.toBeInTheDocument();
  });

  it('marks a generator that changed since it was installed', async () => {
    getRepositoriesMock.mockResolvedValue([REPOSITORY]);
    listGeneratorDirsMock.mockResolvedValue([]);
    getCatalogMock.mockResolvedValue({
      ...CATALOG,
      entries: [
        {
          ...ENTRY,
          installed_as: [
            {
              project: 'nginx',
              revision: 'c'.repeat(40),
              installed_at: '2026-08-19T10:00:00Z',
              outdated: true,
            },
          ],
        },
      ],
    });

    renderPage();
    await openRepository();

    expect(await screen.findByText('update available')).toBeInTheDocument();
    expect(screen.getByText('Install again')).toBeInTheDocument();
  });

  it('opens the details of a generator from its row', async () => {
    getRepositoriesMock.mockResolvedValue([REPOSITORY]);
    listGeneratorDirsMock.mockResolvedValue([]);
    getCatalogMock.mockResolvedValue(CATALOG);

    renderPage();
    await openRepository();
    await userEvent.click(await screen.findByText('Nginx Access Logs'));

    expect(await screen.findByText('generators/web-nginx')).toBeInTheDocument();
    expect(screen.getByText('Branch or tag')).toBeInTheDocument();
    expect(screen.getByText(/in 3 files/)).toBeInTheDocument();
  });

  it('opens the dialog that connects a repository', async () => {
    getRepositoriesMock.mockResolvedValue([REPOSITORY]);
    listGeneratorDirsMock.mockResolvedValue([]);

    renderPage();
    await userEvent.click(await screen.findByText('Connect'));

    await waitFor(() =>
      expect(
        document.querySelector(
          'input[placeholder="https://github.com/eventum-generator/content-packs.git"]'
        )
      ).not.toBeNull()
    );
    expect(document.body.textContent).toContain(
      'Name the repository is referred to by'
    );
    expect(document.body.textContent).toContain(
      'the secret of the keyring holding its'
    );
  });

  it('opens the dialog that installs a generator', async () => {
    getRepositoriesMock.mockResolvedValue([REPOSITORY]);
    listGeneratorDirsMock.mockResolvedValue([]);
    getCatalogMock.mockResolvedValue(CATALOG);

    renderPage();
    await openRepository();
    await screen.findByText('Nginx Access Logs');

    const [installButton] = screen.getAllByText('Install');
    await userEvent.click(installButton!);

    await waitFor(() =>
      expect(document.querySelector('input[value="web-nginx"]')).not.toBeNull()
    );
    expect(document.body.textContent).toContain(
      'Name of the directory the generator is installed into'
    );
  });

  it('proposes a free name for a generator installed already', async () => {
    getRepositoriesMock.mockResolvedValue([REPOSITORY]);
    listGeneratorDirsMock.mockResolvedValue(['web-nginx']);
    getCatalogMock.mockResolvedValue({
      ...CATALOG,
      entries: [
        {
          ...ENTRY,
          installed_as: [
            {
              project: 'web-nginx',
              revision: 'a'.repeat(40),
              installed_at: '2026-08-19T10:00:00Z',
              outdated: false,
            },
          ],
        },
      ],
    });

    renderPage();
    await openRepository();
    await screen.findByText('Nginx Access Logs');

    const [installButton] = screen.getAllByText('Install again');
    await userEvent.click(installButton!);

    await waitFor(() =>
      expect(
        document.querySelector('input[value="web-nginx-2"]')
      ).not.toBeNull()
    );
    expect(document.body.textContent).toContain(
      'Already installed as web-nginx'
    );
  });

  it('reports a repository that cannot be fetched', async () => {
    getRepositoriesMock.mockResolvedValue([REPOSITORY]);
    listGeneratorDirsMock.mockResolvedValue([]);
    getCatalogMock.mockRejectedValue(new Error('unreachable'));

    renderPage();
    await openRepository();

    expect(
      await screen.findByText('Failed to read the catalog')
    ).toBeInTheDocument();
  });
});
