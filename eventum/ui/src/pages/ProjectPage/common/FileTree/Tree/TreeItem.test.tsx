import { ItemInstance } from '@headless-tree/core';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ContextMenuProvider } from 'mantine-contextmenu';
import { basename } from 'pathe';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { TreeItem } from './TreeItem';
import { FileNode } from '@/api/routes/generator-configs/schemas';
import { ProjectNameProvider } from '@/pages/ProjectPage/context/ProjectNameContext';
import { renderWithProviders } from '@/test/render';
import { downloadUrl } from '@/utils/download';

vi.mock('@/api/hooks/useGeneratorConfigs', () => ({
  useCreateGeneratorDirectoryMutation: () => ({ isPending: false }),
}));

vi.mock('@/utils/download', () => ({
  downloadUrl: vi.fn(),
}));

const PROJECT = 'demo';

function itemInstance(
  id: string,
  { isFolder, size }: { isFolder: boolean; size: number | null }
): ItemInstance<FileNode> {
  const data: FileNode = {
    name: basename(id),
    is_dir: isFolder,
    size_in_bytes: size,
    children: isFolder ? [] : null,
  };

  return {
    getId: () => id,
    getItemName: () => data.name,
    getItemData: () => data,
    isFolder: () => isFolder,
    isSelected: () => false,
    isDragTarget: () => false,
    isExpanded: () => false,
    isRenaming: () => false,
    getRenameInputProps: () => ({}),
    startRenaming: vi.fn(),
  } as unknown as ItemInstance<FileNode>;
}

function renderItem(item: ItemInstance<FileNode>) {
  return renderWithProviders(
    <ContextMenuProvider>
      <ProjectNameProvider initialProjectName={PROJECT}>
        <TreeItem
          item={item}
          onCreateDir={vi.fn()}
          onCreateFile={vi.fn()}
          onDeleteFile={vi.fn()}
        />
      </ProjectNameProvider>
    </ContextMenuProvider>
  );
}

async function openContextMenu(item: ItemInstance<FileNode>) {
  const user = userEvent.setup();
  const { container } = renderItem(item);

  const row = container.querySelector('.mantine-NavLink-root');

  if (row === null) {
    throw new Error('the item did not render');
  }

  await user.pointer({ keys: '[MouseRight]', target: row });

  return user;
}

beforeEach(() => {
  vi.mocked(downloadUrl).mockClear();
});

describe('TreeItem', () => {
  it('offers a file for download, labelled with its size', async () => {
    await openContextMenu(
      itemInstance('output/events.json', {
        isFolder: false,
        size: 12 * 1024 * 1024,
      })
    );

    const entry = screen.getByText('Download').closest('.mantine-NavLink-root');

    expect(entry).not.toBeNull();
    // The size is why the entry exists: a file this large cannot be
    // opened in the editor at all.
    expect(entry).toHaveTextContent('12MB');
  });

  it('does not offer a directory for download', async () => {
    await openContextMenu(
      itemInstance('templates', { isFolder: true, size: null })
    );

    expect(screen.queryByText('Download')).not.toBeInTheDocument();
  });

  it('offers the protected config file for download', async () => {
    // It cannot be renamed or deleted here, but taking a copy of it out
    // of Studio changes nothing about the project.
    renderWithProviders(
      <ContextMenuProvider>
        <ProjectNameProvider initialProjectName={PROJECT}>
          <TreeItem
            item={itemInstance('generator.yml', {
              isFolder: false,
              size: 512,
            })}
            isConfigFile
            onCreateDir={vi.fn()}
            onCreateFile={vi.fn()}
            onDeleteFile={vi.fn()}
          />
        </ProjectNameProvider>
      </ContextMenuProvider>
    );

    const user = userEvent.setup();
    await user.pointer({
      keys: '[MouseRight]',
      target: screen.getByText('generator.yml'),
    });

    expect(screen.getByText('Download')).toBeInTheDocument();
    expect(screen.queryByText('Rename')).not.toBeInTheDocument();
  });

  it('downloads the file under its own name, not its path', async () => {
    const user = await openContextMenu(
      itemInstance('output/events.json', {
        isFolder: false,
        size: 2048,
      })
    );

    await user.click(screen.getByText('Download'));

    expect(downloadUrl).toHaveBeenCalledWith(
      '/api/generator-configs/demo/file/output/events.json?download=true',
      'events.json'
    );
  });
});
