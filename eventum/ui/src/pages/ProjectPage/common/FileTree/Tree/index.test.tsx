import { ModalsProvider } from '@mantine/modals';
import { fireEvent, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ContextMenuProvider } from 'mantine-contextmenu';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { Tree } from './index';
import * as configs from '@/api/hooks/useGeneratorConfigs';
import { useInstanceSettings } from '@/api/hooks/useInstance';
import { createFileTreeLookup } from '@/api/routes/generator-configs/modules/file-tree';
import { FileNode } from '@/api/routes/generator-configs/schemas';
import { FileTreeProvider } from '@/pages/ProjectPage/context/FileTreeContext';
import { ProjectNameProvider } from '@/pages/ProjectPage/context/ProjectNameContext';
import { renderWithProviders } from '@/test/render';

vi.mock('@/api/hooks/useGeneratorConfigs');
vi.mock('@/api/hooks/useInstance');

const FILE_TREE: FileNode[] = [
  { name: 'generator.yml', is_dir: false, size_in_bytes: 197, children: null },
  {
    name: 'templates',
    is_dir: true,
    size_in_bytes: null,
    children: [
      {
        name: 'main.jinja',
        is_dir: false,
        size_in_bytes: 20,
        children: null,
      },
    ],
  },
];

const MUTATIONS = {
  move: { mutate: vi.fn(), isPending: false },
  upload: { mutate: vi.fn(), isPending: false },
  createDir: { mutate: vi.fn(), isPending: false },
  remove: { mutate: vi.fn(), isPending: false },
};

function setup(fileTree: FileNode[] = FILE_TREE) {
  vi.mocked(configs.useMoveGeneratorFileMutation).mockReturnValue(
    MUTATIONS.move as never
  );
  vi.mocked(configs.useUploadGeneratorFileMutation).mockReturnValue(
    MUTATIONS.upload as never
  );
  vi.mocked(configs.useCreateGeneratorDirectoryMutation).mockReturnValue(
    MUTATIONS.createDir as never
  );
  vi.mocked(configs.useDeleteGeneratorFileMutation).mockReturnValue(
    MUTATIONS.remove as never
  );
  vi.mocked(useInstanceSettings).mockReturnValue({
    data: { path: { generator_config_filename: 'generator.yml' } },
  } as never);

  renderWithProviders(
    <ProjectNameProvider initialProjectName="web">
      <FileTreeProvider>
        <ModalsProvider>
          {/* The menu of a row is opened by the context-menu provider,
              which the app wraps the whole tree in. */}
          <ContextMenuProvider>
            <Tree fileTreeLookup={createFileTreeLookup(fileTree)} />
          </ContextMenuProvider>
        </ModalsProvider>
      </FileTreeProvider>
    </ProjectNameProvider>
  );

  return { user: userEvent.setup() };
}

beforeEach(() => {
  vi.clearAllMocks();
});

/**
 * The tree is the only way into the files of a project. One of them is
 * not like the others: the configuration file is what makes the project
 * openable at all, so it cannot be renamed, moved or deleted - and the
 * tree has to say so rather than let the request fail.
 */
describe('Tree', () => {
  it('lists what the project holds', () => {
    setup();

    expect(screen.getByText('generator.yml')).toBeInTheDocument();
    expect(screen.getByText('templates')).toBeInTheDocument();
  });

  it('names the size of a file', () => {
    setup();

    expect(screen.getByText('197B')).toBeInTheDocument();
  });

  it('opens a folder to what is inside it', async () => {
    const { user } = setup();

    expect(screen.queryByText('main.jinja')).toBeNull();

    await user.click(screen.getByText('templates'));

    expect(screen.getByText('main.jinja')).toBeInTheDocument();
  });

  it('offers to delete a file of the project', async () => {
    const { user } = setup();

    await user.click(screen.getByText('templates'));
    fireEvent.contextMenu(screen.getByText('main.jinja'));

    expect(
      await screen.findByRole('button', { name: /Delete/ })
    ).toBeInTheDocument();
  });

  it('deletes the file once that is confirmed', async () => {
    const { user } = setup();

    await user.click(screen.getByText('templates'));
    fireEvent.contextMenu(screen.getByText('main.jinja'));
    await user.click(await screen.findByRole('button', { name: /Delete/ }));

    const dialog = await screen.findByRole('dialog');
    await user.click(within(dialog).getByRole('button', { name: 'Delete' }));

    expect(MUTATIONS.remove.mutate).toHaveBeenCalledWith(
      expect.objectContaining({ filepath: 'templates/main.jinja' }),
      expect.anything()
    );
  });

  it('keeps the file when the deletion is refused', async () => {
    const { user } = setup();

    await user.click(screen.getByText('templates'));
    fireEvent.contextMenu(screen.getByText('main.jinja'));
    await user.click(await screen.findByRole('button', { name: /Delete/ }));

    const dialog = await screen.findByRole('dialog');
    await user.click(within(dialog).getByRole('button', { name: 'Cancel' }));

    expect(MUTATIONS.remove.mutate).not.toHaveBeenCalled();
  });

  it('offers no deletion of the file the project is opened by', async () => {
    const { user } = setup();

    fireEvent.contextMenu(screen.getByText('generator.yml'));

    // Losing it would take the project with it, so the menu of that one
    // file offers a download and nothing that changes it.
    expect(
      await screen.findByRole('button', { name: /Download/ })
    ).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Delete/ })).toBeNull();
    expect(screen.queryByRole('button', { name: /Rename/ })).toBeNull();
  });

  it('draws an empty project without failing', () => {
    setup([]);

    expect(screen.queryByText('generator.yml')).toBeNull();
  });
});
