import { ActionIcon, Group, NavLink, Tooltip } from '@mantine/core';
import { modals } from '@mantine/modals';
import { notifications } from '@mantine/notifications';
import { IconFilePlus, IconFolderPlus, IconUpload } from '@tabler/icons-react';
import { useContextMenu } from 'mantine-contextmenu';
import { CSSProperties, FC, useRef } from 'react';

import { FileTree } from '../../common/FileTree';
import { CreateItemModal } from '../../common/FileTree/Tree/CreateItemModal';
import { useProjectName } from '../../hooks/useProjectName';
import {
  useCreateGeneratorDirectoryMutation,
  useUploadGeneratorFileMutation,
} from '@/api/hooks/useGeneratorConfigs';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';

interface ExplorerPanelProps {
  style?: CSSProperties;
}

export const ExplorerPanel: FC<ExplorerPanelProps> = ({ style }) => {
  const { projectName } = useProjectName();
  const uploadFile = useUploadGeneratorFileMutation();
  const createDir = useCreateGeneratorDirectoryMutation();
  const { showContextMenu } = useContextMenu();

  function showError(error: unknown, message: string) {
    notifications.show({
      title: 'Error',
      message: (
        <>
          {message}
          <ShowErrorDetailsAnchor error={error} prependDot />
        </>
      ),
      color: 'red',
    });
  }

  const fileInputRef = useRef<HTMLInputElement>(null);

  function handleUpload(fileList: FileList | null) {
    if (fileList === null) {
      return;
    }
    for (const file of fileList) {
      uploadFile.mutate(
        { name: projectName, filepath: file.name, content: file },
        { onError: (e) => showError(e, `Failed to upload "${file.name}"`) }
      );
    }
  }

  function openCreate(kind: 'file' | 'folder') {
    modals.open({
      title: kind === 'file' ? 'Creating file' : 'Creating directory',
      children: (
        <CreateItemModal
          isLoading={
            kind === 'file' ? uploadFile.isPending : createDir.isPending
          }
          onCreate={(path) => {
            if (kind === 'file') {
              uploadFile.mutate(
                { name: projectName, filepath: path, content: '' },
                {
                  onError: (e) =>
                    showError(e, `Failed to create file "${path}"`),
                }
              );
            } else {
              createDir.mutate(
                { name: projectName, dirpath: path },
                {
                  onError: (e) =>
                    showError(e, `Failed to create directory "${path}"`),
                }
              );
            }
            modals.closeAll();
          }}
        />
      ),
    });
  }

  const rootMenu = showContextMenu(
    [
      {
        key: 'new-file',
        title: (
          <NavLink
            label="New file"
            bdrs="6px"
            p="1px 4px"
            leftSection={<IconFilePlus size={16} />}
          />
        ),
        onClick: () => openCreate('file'),
      },
      {
        key: 'new-folder',
        title: (
          <NavLink
            label="New folder"
            bdrs="6px"
            p="1px 4px"
            leftSection={<IconFolderPlus size={16} />}
          />
        ),
        onClick: () => openCreate('folder'),
      },
    ],
    {
      styles: { root: { borderRadius: '8px', padding: '6px', width: '200px' } },
    }
  );

  return (
    <div className="studio-panel studio-explorer" style={style}>
      <div className="studio-panel-header">
        <span>Explorer</span>
        <Group gap={2}>
          <Tooltip label="New file" withArrow>
            <ActionIcon
              variant="subtle"
              size="sm"
              color="var(--mantine-color-dimmed)"
              aria-label="New file"
              onClick={() => openCreate('file')}
            >
              <IconFilePlus size={16} />
            </ActionIcon>
          </Tooltip>
          <Tooltip label="New folder" withArrow>
            <ActionIcon
              variant="subtle"
              size="sm"
              color="var(--mantine-color-dimmed)"
              aria-label="New folder"
              onClick={() => openCreate('folder')}
            >
              <IconFolderPlus size={16} />
            </ActionIcon>
          </Tooltip>
          <Tooltip label="Upload files" withArrow>
            <ActionIcon
              variant="subtle"
              size="sm"
              color="var(--mantine-color-dimmed)"
              aria-label="Upload files"
              loading={uploadFile.isPending}
              onClick={() => fileInputRef.current?.click()}
            >
              <IconUpload size={16} />
            </ActionIcon>
          </Tooltip>
        </Group>
      </div>
      <div
        className="studio-panel-body studio-panel-body-pad studio-explorer-body"
        onContextMenu={rootMenu}
      >
        <FileTree />
      </div>
      <input
        ref={fileInputRef}
        type="file"
        multiple
        hidden
        onChange={(e) => {
          handleUpload(e.currentTarget.files);
          e.currentTarget.value = '';
        }}
      />
    </div>
  );
};
