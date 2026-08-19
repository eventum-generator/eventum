import { ModalsProvider } from '@mantine/modals';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

import RepositoriesPage from './index';
import { APIError } from '@/api/errors';
import { listGeneratorDirs } from '@/api/routes/generator-configs';
import {
  addRepository,
  checkRepository,
  getCatalog,
  getRepositories,
  installGenerator,
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

vi.mock('@/api/hooks/useSecrets', () => ({
  useSecretNames: () => ({ data: ['git_token'] }),
}));

const navigateMock = vi.fn();

vi.mock('react-router-dom', async (importOriginal) => ({
  ...(await importOriginal<typeof import('react-router-dom')>()),
  useNavigate: () => navigateMock,
}));

const getRepositoriesMock = vi.mocked(getRepositories);
const getCatalogMock = vi.mocked(getCatalog);
const checkRepositoryMock = vi.mocked(checkRepository);
const listGeneratorDirsMock = vi.mocked(listGeneratorDirs);
const installGeneratorMock = vi.mocked(installGenerator);
const addRepositoryMock = vi.mocked(addRepository);

const REPOSITORY: ConnectedRepository = {
  name: 'packs',
  url: 'https://github.com/eventum-generator/content-packs.git',
  ref: 'master',
  status: {
    state: 'available',
    checked_at: '2026-08-19T10:00:00Z',
    reason: null,
  },
};

const ENTRY = {
  name: 'web-nginx',
  path: 'generators/web-nginx',
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
      {
        ...REPOSITORY,
        status: { state: 'unknown', checked_at: null, reason: null },
      },
    ]);
    listGeneratorDirsMock.mockResolvedValue([]);
    checkRepositoryMock.mockResolvedValue({
      state: 'available',
      checked_at: '2026-08-19T10:00:00Z',
      reason: null,
    });

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

  it('offers to open a generator already installed', async () => {
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

    // The badge is what carries at a glance, the action is what the
    // row is for once the generator is in the workspace.
    expect(await screen.findByText('installed')).toBeInTheDocument();
    expect(screen.getByText('Open')).toBeInTheDocument();
    expect(screen.queryByText('Install')).not.toBeInTheDocument();
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
    expect(screen.getByText('Open')).toBeInTheDocument();
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

  it('offers to connect anyway when the repository did not answer', async () => {
    getRepositoriesMock.mockResolvedValue([]);
    listGeneratorDirsMock.mockResolvedValue([]);
    addRepositoryMock.mockRejectedValueOnce(
      new APIError({
        message: 'Bad gateway',
        response: {
          status: 502,
          data: { detail: 'Failed to reach repository: refused' },
        } as never,
      })
    );

    renderPage();
    await userEvent.click(await screen.findByText('Connect repository'));

    const url = 'https://github.com/eventum-generator/content-packs.git';
    await waitFor(() =>
      expect(
        document.querySelector(`input[placeholder="${url}"]`)
      ).not.toBeNull()
    );

    const inputs = document.querySelectorAll('.mantine-Modal-content input');
    await userEvent.type(inputs[0] as HTMLElement, 'packs');
    await userEvent.type(inputs[1] as HTMLElement, url);

    const submit = screen
      .getAllByText('Connect')
      .find((element) => element.closest('.mantine-Modal-content'));
    await userEvent.click(submit!);

    const anyway = await screen.findByText('Connect anyway');
    addRepositoryMock.mockResolvedValueOnce();
    await userEvent.click(anyway);

    await waitFor(() =>
      expect(addRepositoryMock).toHaveBeenLastCalledWith(
        expect.objectContaining({ name: 'packs' }),
        false
      )
    );
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

    // Installing another copy is a step deeper, in the card of the
    // generator, since the row is about the project already there.
    await userEvent.click(await screen.findByText('Nginx Access Logs'));
    await userEvent.click(await screen.findByText('Install another copy'));

    await waitFor(() =>
      expect(
        document.querySelector('input[value="web-nginx-2"]')
      ).not.toBeNull()
    );
    expect(document.body.textContent).toContain(
      'Already installed as web-nginx'
    );
  });

  it('opens the project a generator is installed as', async () => {
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
    await userEvent.click(await screen.findByText('Open'));

    expect(navigateMock).toHaveBeenCalledWith('/projects/nginx');
  });

  it('installs the generator the dialog was opened for', async () => {
    getRepositoriesMock.mockResolvedValue([REPOSITORY]);
    listGeneratorDirsMock.mockResolvedValue([]);
    getCatalogMock.mockResolvedValue(CATALOG);
    installGeneratorMock.mockResolvedValue();

    renderPage();
    await openRepository();
    await screen.findByText('Nginx Access Logs');

    const [installButton] = screen.getAllByText('Install');
    await userEvent.click(installButton!);
    await waitFor(() =>
      expect(document.querySelector('input[value="web-nginx"]')).not.toBeNull()
    );

    const submit = screen
      .getAllByText('Install')
      .find((element) => element.closest('.mantine-Modal-content'));
    await userEvent.click(submit!);

    await waitFor(() =>
      expect(installGeneratorMock).toHaveBeenCalledWith(
        'packs',
        'web-nginx',
        'web-nginx'
      )
    );
  });

  it('connects the repository the form was filled with', async () => {
    getRepositoriesMock.mockResolvedValue([]);
    listGeneratorDirsMock.mockResolvedValue([]);
    addRepositoryMock.mockResolvedValue();

    renderPage();
    await userEvent.click(await screen.findByText('Connect repository'));

    const url = 'https://github.com/eventum-generator/content-packs.git';
    await waitFor(() =>
      expect(
        document.querySelector(`input[placeholder="${url}"]`)
      ).not.toBeNull()
    );

    const inputs = document.querySelectorAll('.mantine-Modal-content input');
    await userEvent.type(inputs[0] as HTMLElement, 'packs');
    await userEvent.type(inputs[1] as HTMLElement, url);

    const submit = screen
      .getAllByText('Connect')
      .find((element) => element.closest('.mantine-Modal-content'));
    await userEvent.click(submit!);

    await waitFor(() =>
      expect(addRepositoryMock).toHaveBeenCalledWith(
        {
          name: 'packs',
          url,
          ref: undefined,
          username: undefined,
          secret: undefined,
        },
        true
      )
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
