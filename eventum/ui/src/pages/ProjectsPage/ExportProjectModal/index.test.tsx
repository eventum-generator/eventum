import { ModalsProvider } from '@mantine/modals';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ExportProjectModal } from './index';
import { useGeneratorFileTree } from '@/api/hooks/useGeneratorConfigs';
import { useInstanceSettings } from '@/api/hooks/useInstance';
import { FileNode } from '@/api/routes/generator-configs/schemas';
import { renderWithProviders } from '@/test/render';
import { downloadUrl } from '@/utils/download';

vi.mock('@/api/hooks/useGeneratorConfigs');
vi.mock('@/api/hooks/useInstance');
vi.mock('@/utils/download');

function file(name: string, size: number): FileNode {
  return { name, is_dir: false, size_in_bytes: size, children: null };
}

function dir(name: string, children: FileNode[]): FileNode {
  return { name, is_dir: true, size_in_bytes: null, children };
}

const TREE: FileNode[] = [
  file('generator.yml', 100),
  dir('output', [file('events.json', 4000)]),
  dir('templates', [file('main.jinja', 900)]),
];

function setup(
  tree: FileNode[] | null = TREE,
  state: Record<string, unknown> = {}
) {
  vi.mocked(useGeneratorFileTree).mockReturnValue({
    data: tree ?? undefined,
    isLoading: false,
    isError: false,
    error: null,
    ...state,
  } as unknown as ReturnType<typeof useGeneratorFileTree>);

  renderWithProviders(
    <ModalsProvider>
      <ExportProjectModal projectName="web" />
    </ModalsProvider>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(useInstanceSettings).mockReturnValue({
    data: { path: { generator_config_filename: 'generator.yml' } },
  } as unknown as ReturnType<typeof useInstanceSettings>);
});

/**
 * An export is a browser download of an archive the backend builds, and
 * what goes into it is chosen here. The configuration file is the one
 * thing the archive cannot be without - a project without it is not a
 * project the studio can open.
 */
describe('ExportProjectModal', () => {
  it('lists what the project holds', () => {
    setup();

    expect(screen.getByText('generator.yml')).toBeInTheDocument();
    expect(screen.getByText('output')).toBeInTheDocument();
    expect(screen.getByText('templates')).toBeInTheDocument();
  });

  it('ticks everything to begin with', () => {
    setup();

    for (const box of screen.getAllByRole('checkbox')) {
      expect(box).toBeChecked();
    }
  });

  it('does not let the configuration file be left out', () => {
    setup();

    expect(
      screen.getByRole('checkbox', { name: /generator.yml/ })
    ).toBeDisabled();
  });

  it('sums what a directory holds, not the directory itself', () => {
    setup();

    // The output directory itself carries no size; the file under it
    // does, so the row has to report that rather than nothing.
    const label = screen.getByRole('checkbox', { name: /output/ });
    const row = label.closest('.mantine-Group-root')?.parentElement;

    expect(row?.textContent ?? '').toMatch(/3\.9\d?KB/);
  });

  it('reports the size of everything still ticked', () => {
    setup();

    // 100 B of config, 900 B of template and 4000 B of output.
    expect(screen.getByText(/before compression/).textContent).toMatch(
      /4\.8\d?KB/
    );
  });

  it('drops what is unticked from that size', async () => {
    const user = userEvent.setup();
    setup();

    await user.click(screen.getByRole('checkbox', { name: /output/ }));

    expect(screen.getByText(/before compression/).textContent).toMatch(/1000B/);
  });

  it('downloads the archive of everything ticked', async () => {
    const user = userEvent.setup();
    setup();

    await user.click(screen.getByRole('button', { name: 'Export' }));

    expect(downloadUrl).toHaveBeenCalledTimes(1);

    const [url, filename] = vi.mocked(downloadUrl).mock.calls[0]!;

    expect(url).toContain('/generator-configs/web/export');
    expect(filename).toBe('web.zip');
  });

  it('names what to leave out in the request', async () => {
    const user = userEvent.setup();
    setup();

    await user.click(screen.getByRole('checkbox', { name: /output/ }));
    await user.click(screen.getByRole('button', { name: 'Export' }));

    expect(vi.mocked(downloadUrl).mock.calls[0]?.[0]).toContain(
      'exclude=output'
    );
  });

  it('waits while the project files are being read', () => {
    setup(null, { isLoading: true });

    expect(screen.queryByRole('checkbox')).not.toBeInTheDocument();
  });

  it('reports a failure to read them', () => {
    setup(null, {
      isLoading: false,
      isError: true,
      error: new Error('no connection'),
    });

    expect(
      screen.getByText('Failed to load project files')
    ).toBeInTheDocument();
  });
});
