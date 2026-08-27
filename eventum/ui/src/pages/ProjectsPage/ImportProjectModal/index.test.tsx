import { ModalsProvider } from '@mantine/modals';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { readZipEntryNames } from './archive';
import { ImportProjectModal } from './index';
import { useImportGeneratorProjectMutation } from '@/api/hooks/useGeneratorConfigs';
import { useInstanceSettings } from '@/api/hooks/useInstance';
import { renderWithProviders } from '@/test/render';

vi.mock('@/api/hooks/useGeneratorConfigs');
vi.mock('@/api/hooks/useInstance');
vi.mock('./archive', async (importOriginal) => {
  const original = await importOriginal<typeof import('./archive')>();

  return { ...original, readZipEntryNames: vi.fn() };
});

const importProject = { mutate: vi.fn(), isPending: false };

function archiveFile(name = 'archive(1).zip', size = 2048): File {
  const file = new File(['zip'], name, { type: 'application/zip' });

  Object.defineProperty(file, 'size', { value: size });

  return file;
}

function setup(existing: string[] = []) {
  renderWithProviders(
    <ModalsProvider>
      <ImportProjectModal existingProjectNames={existing} />
    </ModalsProvider>
  );

  // The picker input is hidden, so the file is handed to it directly -
  // the same input the Choose button clicks.
  return document.querySelector<HTMLInputElement>('input[type="file"]')!;
}

beforeEach(() => {
  vi.clearAllMocks();
  importProject.mutate.mockReset();
  vi.mocked(useImportGeneratorProjectMutation).mockReturnValue(
    importProject as unknown as ReturnType<
      typeof useImportGeneratorProjectMutation
    >
  );
  vi.mocked(useInstanceSettings).mockReturnValue({
    data: { path: { generator_config_filename: 'generator.yml' } },
  } as unknown as ReturnType<typeof useInstanceSettings>);
  vi.mocked(readZipEntryNames).mockResolvedValue([]);
});

/**
 * An import writes a project directory named here, so the name matters
 * more than the archive does. The directory inside the archive names
 * the project better than the file does - a project downloaded as
 * `archive(1).zip` should still import under its own name.
 */
describe('ImportProjectModal', () => {
  it('says nothing is selected to begin with', () => {
    setup();

    expect(screen.getByText('No archive selected')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Choose/ })).toBeInTheDocument();
  });

  it('offers no import until an archive is chosen', () => {
    setup();

    expect(screen.getByRole('button', { name: 'Import' })).toBeDisabled();
  });

  it('names the archive once one is chosen', async () => {
    const user = userEvent.setup();
    const input = setup();

    await user.upload(input, archiveFile('web-nginx.zip'));

    expect(await screen.findByText('web-nginx.zip')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Replace/ })).toBeInTheDocument();
  });

  it('proposes the name of the directory the archive carries', async () => {
    const user = userEvent.setup();
    vi.mocked(readZipEntryNames).mockResolvedValue([
      'web-nginx/generator.yml',
      'web-nginx/templates/main.jinja',
    ]);

    const input = setup();

    await user.upload(input, archiveFile('archive(1).zip'));

    await waitFor(() =>
      expect(screen.getByRole('textbox', { name: /Project name/ })).toHaveValue(
        'web-nginx'
      )
    );
  });

  it('falls back to the archive name when it carries no directory', async () => {
    const user = userEvent.setup();
    vi.mocked(readZipEntryNames).mockResolvedValue(['generator.yml']);

    const input = setup();

    await user.upload(input, archiveFile('web-nginx.zip'));

    await waitFor(() =>
      expect(screen.getByRole('textbox', { name: /Project name/ })).toHaveValue(
        'web-nginx'
      )
    );
  });

  it('keeps a name the user typed when another archive is chosen', async () => {
    const user = userEvent.setup();
    const input = setup();

    await user.upload(input, archiveFile('first.zip'));
    await waitFor(() =>
      expect(screen.getByRole('textbox', { name: /Project name/ })).toHaveValue(
        'first'
      )
    );

    const name = screen.getByRole('textbox', { name: /Project name/ });
    await user.clear(name);
    await user.type(name, 'mine');

    await user.upload(input, archiveFile('second.zip'));

    expect(name).toHaveValue('mine');
  });

  it('refuses a name another project already has', async () => {
    const user = userEvent.setup();
    const input = setup(['web']);

    await user.upload(input, archiveFile('other.zip'));

    const name = await screen.findByRole('textbox', { name: /Project name/ });
    await user.clear(name);
    await user.type(name, 'web');

    expect(screen.getByRole('button', { name: 'Import' })).toBeDisabled();
  });

  it('sends the archive under the name that was settled on', async () => {
    const user = userEvent.setup();
    const input = setup();

    await user.upload(input, archiveFile('web-nginx.zip'));
    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'Import' })).toBeEnabled()
    );

    await user.click(screen.getByRole('button', { name: 'Import' }));

    expect(importProject.mutate).toHaveBeenCalledTimes(1);

    const sent = importProject.mutate.mock.calls[0]?.[0] as {
      name: string;
      archive: File;
    };

    expect(sent.name).toBe('web-nginx');
    expect(sent.archive.name).toBe('web-nginx.zip');
  });

  it('accepts only zip archives from the picker', () => {
    const input = setup();

    expect(input.accept).toContain('.zip');
  });
});
