import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

import RepositoriesPage from './index';
import { listGeneratorDirs } from '@/api/routes/generator-configs';
import { getCatalog, getRepositories } from '@/api/routes/repositories';
import { renderWithProviders } from '@/test/render';

vi.mock('@/api/routes/repositories', () => ({
  getRepositories: vi.fn(),
  getCatalog: vi.fn(),
  refreshCatalog: vi.fn(),
  addRepository: vi.fn(),
  deleteRepository: vi.fn(),
  installGenerator: vi.fn(),
}));

vi.mock('@/api/routes/generator-configs', () => ({
  listGeneratorDirs: vi.fn(),
}));

const getRepositoriesMock = vi.mocked(getRepositories);
const getCatalogMock = vi.mocked(getCatalog);
const listGeneratorDirsMock = vi.mocked(listGeneratorDirs);

const CATALOG = {
  revision: 'a'.repeat(40),
  refreshed_at: '2026-08-19T10:00:00Z',
  entries: [
    {
      name: 'web-nginx',
      title: 'Nginx Access Logs',
      summary: 'Produces nginx access log entries.',
      file_count: 3,
      size: 2048,
    },
  ],
};

function renderPage() {
  return renderWithProviders(
    <MemoryRouter>
      <RepositoriesPage />
    </MemoryRouter>
  );
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
    getRepositoriesMock.mockResolvedValue([
      { name: 'packs', url: 'https://example.com/packs.git', ref: 'master' },
    ]);
    listGeneratorDirsMock.mockResolvedValue([]);

    renderPage();

    expect(await screen.findByText('packs')).toBeInTheDocument();
    expect(getCatalogMock).not.toHaveBeenCalled();
  });

  it('reads the catalog when a repository is opened', async () => {
    getRepositoriesMock.mockResolvedValue([
      { name: 'packs', url: 'https://example.com/packs.git' },
    ]);
    listGeneratorDirsMock.mockResolvedValue([]);
    getCatalogMock.mockResolvedValue(CATALOG);

    renderPage();

    await userEvent.click(await screen.findByText('packs'));

    expect(await screen.findByText('Nginx Access Logs')).toBeInTheDocument();
    await waitFor(() => expect(getCatalogMock).toHaveBeenCalledWith('packs'));
  });

  it('reports a repository that cannot be fetched', async () => {
    getRepositoriesMock.mockResolvedValue([
      { name: 'packs', url: 'https://example.com/packs.git' },
    ]);
    listGeneratorDirsMock.mockResolvedValue([]);
    getCatalogMock.mockRejectedValue(new Error('unreachable'));

    renderPage();

    await userEvent.click(await screen.findByText('packs'));

    expect(
      await screen.findByText('Failed to read the catalog')
    ).toBeInTheDocument();
  });
});
