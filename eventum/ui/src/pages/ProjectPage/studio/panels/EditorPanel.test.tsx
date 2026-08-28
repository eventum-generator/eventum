import { ItemInstance } from '@headless-tree/core';
import { ModalsProvider } from '@mantine/modals';
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ReactNode } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { StudioShellContext, StudioShellValue } from '../context';
import { EditorPanel } from './EditorPanel';
import { useGeneratorFileTree } from '@/api/hooks/useGeneratorConfigs';
import { FileNode } from '@/api/routes/generator-configs/schemas';
import { renderWithProviders } from '@/test/render';

vi.mock('@/api/hooks/useGeneratorConfigs');

// The editor itself is CodeMirror over the content of one file; what is
// under test here is the strip of tabs above it.
vi.mock('../../common/EditorTab/FileEditor', () => ({
  FileEditor: ({ filePath }: { filePath: string }) => (
    <div>editing {filePath}</div>
  ),
}));

const FILE_TREE: FileNode[] = [
  {
    name: 'templates',
    is_dir: true,
    size_in_bytes: null,
    children: [
      { name: 'main.jinja', is_dir: false, size_in_bytes: 20, children: null },
      { name: 'other.jinja', is_dir: false, size_in_bytes: 20, children: null },
    ],
  },
];

/** An opened file, as the tree hands it over. */
function opened(id: string): ItemInstance<FileNode> {
  return {
    getId: () => id,
    // The tab draws the icon of the file, which asks the item what it is.
    isFolder: () => false,
    getItemName: () => id.split('/').pop() ?? id,
    getItemData: () => ({
      name: id.split('/').pop() ?? id,
      is_dir: false,
      size_in_bytes: 20,
      children: null,
    }),
  } as unknown as ItemInstance<FileNode>;
}

interface Options {
  openedIds?: string[];
  activeId?: string;
  savedStatuses?: Record<string, boolean>;
}

function setup(options: Options = {}) {
  const openedIds = options.openedIds ?? ['templates/main.jinja'];

  vi.mocked(useGeneratorFileTree).mockReturnValue({
    data: FILE_TREE,
    isSuccess: true,
    isLoading: false,
    isError: false,
    error: null,
  } as unknown as ReturnType<typeof useGeneratorFileTree>);

  const shell = {
    projectName: 'web',
    openedItems: openedIds.map((id) => opened(id)),
    activeId: options.activeId ?? openedIds[0],
    activateItem: vi.fn(),
    closeItem: vi.fn(),
    savedStatuses: options.savedStatuses ?? {},
    setSaved: vi.fn(),
    registerSaver: vi.fn(),
    unregisterSaver: vi.fn(),
    saveFile: vi.fn(),
  } as unknown as StudioShellValue;

  const wrap = (children: ReactNode) => (
    <StudioShellContext.Provider value={shell}>
      <ModalsProvider>{children}</ModalsProvider>
    </StudioShellContext.Provider>
  );

  renderWithProviders(wrap(<EditorPanel />));

  return { shell, user: userEvent.setup() };
}

/** The tab of one file, by the name it shows. */
function tab(name: string): HTMLElement {
  const node = screen.getByText(name).closest('.studio-tab');

  if (node === null) {
    throw new Error(`${name} has no tab`);
  }

  return node as HTMLElement;
}

beforeEach(() => {
  vi.clearAllMocks();
});

/**
 * Files are edited in tabs, and every open one stays mounted so it keeps
 * what was typed into it while another is looked at. Closing one with
 * unsaved changes has to ask first - but only when there is a file to
 * lose: a tab of something that is no longer in the project has nothing
 * to save back.
 */
describe('EditorPanel', () => {
  it('says what the editor is for while nothing is open', () => {
    setup({ openedIds: [] });

    expect(
      screen.getByText('Select a file in the Explorer to open it here.')
    ).toBeInTheDocument();
  });

  it('offers no save while nothing is open', () => {
    setup({ openedIds: [] });

    expect(screen.queryByRole('button', { name: 'Save file' })).toBeNull();
  });

  it('draws a tab per open file', () => {
    setup({
      openedIds: ['templates/main.jinja', 'templates/other.jinja'],
    });

    expect(tab('main.jinja')).toBeInTheDocument();
    expect(tab('other.jinja')).toBeInTheDocument();
  });

  it('keeps every open file mounted and shows the active one', () => {
    setup({
      openedIds: ['templates/main.jinja', 'templates/other.jinja'],
      activeId: 'templates/other.jinja',
    });

    // Both are mounted so each keeps what was typed into it; only one is
    // shown.
    const surfaces = [
      ...document.querySelectorAll<HTMLElement>('.studio-editor-file'),
    ];

    expect(surfaces).toHaveLength(2);
    expect(surfaces.filter((surface) => !surface.hidden)).toHaveLength(1);
    expect(screen.getByText('editing templates/other.jinja')).toBeVisible();
  });

  it('opens the file whose tab was used', async () => {
    const { shell, user } = setup({
      openedIds: ['templates/main.jinja', 'templates/other.jinja'],
    });

    await user.click(screen.getByText('other.jinja'));

    expect(shell.activateItem).toHaveBeenCalledTimes(1);
  });

  it('offers a save only for a file with something to save', () => {
    setup({ savedStatuses: { 'templates/main.jinja': true } });

    expect(screen.getByRole('button', { name: 'Save file' })).toBeDisabled();
  });

  it('offers a save for a file that was edited', async () => {
    const { shell, user } = setup({
      savedStatuses: { 'templates/main.jinja': false },
    });

    const save = screen.getByRole('button', { name: 'Save file' });
    expect(save).toBeEnabled();

    await user.click(save);

    expect(shell.saveFile).toHaveBeenCalledWith('templates/main.jinja');
  });

  it('closes a saved file without asking', async () => {
    const { shell, user } = setup({
      savedStatuses: { 'templates/main.jinja': true },
    });

    await user.click(
      within(tab('main.jinja')).getByRole('button', { name: 'Close file' })
    );

    expect(shell.closeItem).toHaveBeenCalledTimes(1);
  });

  it('asks before closing a file that was edited', async () => {
    const { shell, user } = setup({
      savedStatuses: { 'templates/main.jinja': false },
    });

    await user.click(
      within(tab('main.jinja')).getByRole('button', { name: 'Close file' })
    );

    const dialog = await screen.findByRole('dialog');
    expect(dialog).toHaveTextContent('Unsaved changes');
    expect(shell.closeItem).not.toHaveBeenCalled();

    await user.click(within(dialog).getByRole('button', { name: 'Continue' }));

    expect(shell.closeItem).toHaveBeenCalledTimes(1);
  });

  it('closes a file that is no longer in the project without asking', async () => {
    const { shell, user } = setup({
      openedIds: ['templates/gone.jinja'],
      savedStatuses: { 'templates/gone.jinja': false },
    });

    // There is nothing to save it back into, so a confirmation would
    // offer a choice that does not exist.
    await user.click(
      within(tab('gone.jinja')).getByRole('button', { name: 'Close file' })
    );

    expect(shell.closeItem).toHaveBeenCalledTimes(1);
  });

  it('marks a tab of a file that is no longer in the project', () => {
    setup({ openedIds: ['templates/gone.jinja'] });

    expect(document.querySelector('[data-missing="true"]')).not.toBeNull();
  });
});
