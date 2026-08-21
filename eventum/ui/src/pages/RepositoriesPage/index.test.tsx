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
  discoverRepositories,
  getCatalog,
  getRepositories,
  installGenerator,
} from '@/api/routes/repositories';
import {
  Catalog,
  ConnectedRepository,
  Discovery,
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
  discoverRepositories: vi.fn(),
  MAX_DISCOVERY_PAGES: 10,
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
const discoverRepositoriesMock = vi.mocked(discoverRepositories);

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

const DISCOVERY: Discovery = {
  topic: 'eventum-generators',
  query: '',
  entries: [
    {
      name: 'content-packs',
      full_name: 'eventum-generator/content-packs',
      url: 'https://github.com/eventum-generator/content-packs.git',
      page_url: 'https://github.com/eventum-generator/content-packs',
      owner: 'eventum-generator',
      description: 'Ready-made generators',
      topics: ['eventum-generators'],
      stars: 42,
      updated_at: '2026-08-01T10:00:00Z',
      license: 'Apache-2.0',
      archived: false,
      official: true,
      connected: false,
    },
  ],
  total_count: 1,
  refreshed_at: '2026-08-19T10:00:00Z',
  rate: { remaining: 9, reset_at: '2026-08-19T10:05:00Z' },
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
    expect(document.body.textContent).toContain('its password or access token');
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

  it('connects with the reference of the secret that was picked', async () => {
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
    await userEvent.click(screen.getByLabelText('Use a keyring secret'));
    await userEvent.click(await screen.findByText('git_token'));

    const reference = '${secrets.git_token}';
    const submit = screen
      .getAllByText('Connect')
      .find((element) => element.closest('.mantine-Modal-content'));
    await userEvent.click(submit!);

    await waitFor(() =>
      expect(addRepositoryMock).toHaveBeenCalledWith(
        expect.objectContaining({ password: reference }),
        true
      )
    );
  });

  it('connects with a password typed in place', async () => {
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
    const typed = 'ghp_token';
    await userEvent.type(screen.getByLabelText('Password'), typed);

    const submit = screen
      .getAllByText('Connect')
      .find((element) => element.closest('.mantine-Modal-content'));
    await userEvent.click(submit!);

    await waitFor(() =>
      expect(addRepositoryMock).toHaveBeenCalledWith(
        expect.objectContaining({ password: typed }),
        true
      )
    );
  });

  it('refuses a password naming a substitution of another kind', async () => {
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
    // `{` opens a key descriptor for userEvent, so it is doubled to
    // type the token itself.
    await userEvent.type(
      screen.getByLabelText('Password'),
      '${{params.git_token}'
    );

    const submit = screen
      .getAllByText('Connect')
      .find((element) => element.closest('.mantine-Modal-content'));
    await userEvent.click(submit!);

    expect(
      await screen.findByText(
        'Only a "${secrets.<name>}" reference is substituted here'
      )
    ).toBeInTheDocument();
    expect(addRepositoryMock).not.toHaveBeenCalled();
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
          password: undefined,
        },
        true
      )
    );
  });

  it('lists what is published in the open', async () => {
    getRepositoriesMock.mockResolvedValue([]);
    listGeneratorDirsMock.mockResolvedValue([]);
    discoverRepositoriesMock.mockResolvedValue(DISCOVERY);

    renderPage();
    await userEvent.click(await screen.findByText('Discover'));

    expect(
      await screen.findByText('eventum-generator/content-packs')
    ).toBeInTheDocument();
    // What the list is must be stated, not implied.
    expect(
      screen.getByText('Community repositories are not reviewed')
    ).toBeInTheDocument();
  });

  it('opens the connect dialog on a published repository', async () => {
    getRepositoriesMock.mockResolvedValue([]);
    listGeneratorDirsMock.mockResolvedValue([]);
    discoverRepositoriesMock.mockResolvedValue(DISCOVERY);

    renderPage();
    await userEvent.click(await screen.findByText('Discover'));
    await userEvent.click(
      await screen.findByRole('button', { name: 'Connect' })
    );

    // The dialog opens on the repository that was picked, so nothing
    // has to be typed to connect it.
    const url = await screen.findByDisplayValue(
      'https://github.com/eventum-generator/content-packs.git'
    );
    expect(url).toBeInTheDocument();
    expect(screen.getByDisplayValue('content-packs')).toBeInTheDocument();
  });

  it('does not offer to connect what is already connected', async () => {
    getRepositoriesMock.mockResolvedValue([]);
    listGeneratorDirsMock.mockResolvedValue([]);
    discoverRepositoriesMock.mockResolvedValue({
      ...DISCOVERY,
      entries: [{ ...DISCOVERY.entries[0]!, connected: true }],
    });

    renderPage();
    await userEvent.click(await screen.findByText('Discover'));

    expect(
      await screen.findByRole('button', { name: 'Connected' })
    ).toBeDisabled();
  });

  it('pages through what is published', async () => {
    getRepositoriesMock.mockResolvedValue([]);
    listGeneratorDirsMock.mockResolvedValue([]);

    const second = {
      ...DISCOVERY.entries[0]!,
      name: 'more-packs',
      full_name: 'someone/more-packs',
      url: 'https://github.com/someone/more-packs.git',
      official: false,
    };
    discoverRepositoriesMock.mockImplementation((_query, page) =>
      Promise.resolve(
        page === 1
          ? { ...DISCOVERY, total_count: 2 }
          : { ...DISCOVERY, total_count: 2, entries: [second] }
      )
    );

    renderPage();
    await userEvent.click(await screen.findByText('Discover'));
    await userEvent.click(
      await screen.findByRole('button', { name: 'Load more' })
    );

    expect(await screen.findByText('someone/more-packs')).toBeInTheDocument();
    // Everything the search matched is listed, so nothing is left to load.
    expect(
      screen.queryByRole('button', { name: 'Load more' })
    ).not.toBeInTheDocument();
    expect(discoverRepositoriesMock).toHaveBeenLastCalledWith('', 2);
  });

  it('says what is left out when the pages run out', async () => {
    getRepositoriesMock.mockResolvedValue([]);
    listGeneratorDirsMock.mockResolvedValue([]);
    // A page that came back short is the last one, whatever the total
    // says - the search reaches only so far.
    discoverRepositoriesMock.mockResolvedValue({
      ...DISCOVERY,
      total_count: 400,
      entries: [],
    });

    renderPage();
    await userEvent.click(await screen.findByText('Discover'));

    expect(
      await screen.findByText('Nothing published matches')
    ).toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: 'Load more' })
    ).not.toBeInTheDocument();
  });

  it('reports a search that was refused', async () => {
    getRepositoriesMock.mockResolvedValue([]);
    listGeneratorDirsMock.mockResolvedValue([]);
    discoverRepositoriesMock.mockRejectedValue(new Error('rate limited'));

    renderPage();
    await userEvent.click(await screen.findByText('Discover'));

    expect(
      await screen.findByText('Failed to search published repositories')
    ).toBeInTheDocument();
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
