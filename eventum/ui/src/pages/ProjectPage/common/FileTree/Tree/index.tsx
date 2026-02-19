import {
  dragAndDropFeature,
  hotkeysCoreFeature,
  renamingFeature,
  selectionFeature,
  syncDataLoaderFeature,
} from '@headless-tree/core';
import { useTree } from '@headless-tree/react';
import { Box, Stack, Text } from '@mantine/core';
import { modals } from '@mantine/modals';
import { notifications } from '@mantine/notifications';
import { dirname, join } from 'pathe';
import { FC, useEffect } from 'react';

import { TreeItem } from './TreeItem';
import {
  useCreateGeneratorDirectoryMutation,
  useDeleteGeneratorFileMutation,
  useMoveGeneratorFileMutation,
  useUploadGeneratorFileMutation,
} from '@/api/hooks/useGeneratorConfigs';
import { createFileTreeLookup } from '@/api/routes/generator-configs/modules/file-tree';
import { FileNode } from '@/api/routes/generator-configs/schemas';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';
import { useFileTree } from '@/pages/ProjectPage/hooks/useFileTree';
import { useProjectName } from '@/pages/ProjectPage/hooks/useProjectName';

interface TreeProps {
  fileTreeLookup: ReturnType<typeof createFileTreeLookup>;
}

export const Tree: FC<TreeProps> = ({ fileTreeLookup }) => {
  'use no memo';

  const { selectedItem, setSelectedItem } = useFileTree();
  const { projectName } = useProjectName();
  const moveFile = useMoveGeneratorFileMutation();
  const uploadFile = useUploadGeneratorFileMutation();
  const createDir = useCreateGeneratorDirectoryMutation();
  const deleteFile = useDeleteGeneratorFileMutation();

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

  function handleCreateDir(dirpath: string) {
    createDir.mutate(
      {
        name: projectName,
        dirpath: dirpath,
      },
      {
        onError: (error) => {
          showError(error, `Failed to create directory "${dirpath}"`);
        },
      }
    );
  }

  function handleUploadFile(filepath: string, file: File) {
    uploadFile.mutate(
      {
        name: projectName,
        filepath: filepath,
        content: file,
      },
      {
        onError: (error) => {
          showError(error, `Failed to upload file "${file.name}"`);
        },
      }
    );
  }

  function handleCreateEmptyFile(filepath: string) {
    uploadFile.mutate(
      {
        name: projectName,
        filepath: filepath,
        content: '',
      },
      {
        onError: (error) => {
          showError(error, `Failed to create file "${filepath}"`);
        },
      }
    );
  }

  function handleMoveFile(source: string, destination: string) {
    moveFile.mutate(
      {
        name: projectName,
        source: source,
        destination: destination,
      },
      {
        onError: (error) => {
          showError(error, `Failed to move file "${source}"`);
        },
      }
    );
  }

  function handleDeleteFile(filepath: string) {
    deleteFile.mutate(
      {
        name: projectName,
        filepath: filepath,
      },
      {
        onError: (error) => {
          showError(error, `Failed to delete file "${filepath}"`);
        },
      }
    );
  }

  const tree = useTree<FileNode>({
    features: [
      syncDataLoaderFeature,
      selectionFeature,
      hotkeysCoreFeature,
      dragAndDropFeature,
      renamingFeature,
    ],
    initialState: {},
    rootItemId: '',
    getItemName: (item) => item.getItemData().name,
    isItemFolder: (item) => item.getItemData().is_dir,
    openOnDropDelay: 500,
    indent: 20,
    dataLoader: {
      getItem: (itemId) =>
        fileTreeLookup.items.get(itemId) ?? {
          name: '',
          is_dir: false,
          children: [],
        },
      getChildren: (itemId) => fileTreeLookup.children.get(itemId) ?? [],
    },
    onPrimaryAction: (item) => {
      setSelectedItem(item);
    },
    onRename: (item, newName) => {
      const oldName = item.getItemName();
      const directory = dirname(item.getId());

      const source = join(directory, oldName);
      const destination = join(directory, newName);
      handleMoveFile(source, destination);
    },
    onDrop: (items, target) => {
      const destination = target.item.getId();

      for (const item of items) {
        const source = item.getId();
        const sourceDirectory = dirname(source);

        if (sourceDirectory === destination) {
          continue;
        }

        handleMoveFile(source, destination);
      }
    },
    canDropForeignDragObject: (dataTransfer, target) => {
      return dataTransfer.types.includes('Files') && target.item.isFolder();
    },
    onDropForeignDragObject: (dataTransfer, target) => {
      const targetDir = target.item.getId();

      for (const file of dataTransfer.files) {
        const filepath = join(targetDir, file.name);
        handleUploadFile(filepath, file);
      }
    },
    hotkeys: {
      customDelete: {
        hotkey: 'Delete',
        handler: (_, tree) => {
          const items = tree.getSelectedItems();

          if (items.length > 0) {
            const item = items[0]!;
            modals.openConfirmModal({
              title: 'Deleting file',
              children: (
                <Text size="sm">
                  File &quot;<b>{item.getId()}</b>&quot; will be deleted. Do you
                  want to continue?
                </Text>
              ),
              labels: { confirm: 'Confirm', cancel: 'Cancel' },
              onConfirm: () => handleDeleteFile(item.getId()),
            });
          }
        },
      },
    },
  });

  useEffect(() => {
    if (selectedItem === undefined) {
      return;
    }

    const pathSegments = selectedItem.getId().split('/').slice(1);
    let currentPath = '.';

    for (const segment of pathSegments.slice(0, -1)) {
      currentPath += '/' + segment;
      const parentItem = tree.getItemInstance(currentPath);
      parentItem.expand();
    }

    tree.setSelectedItems([selectedItem.getId()]);
  }, [tree, selectedItem]);

  useEffect(() => {
    tree.rebuildTree();
  }, [tree, fileTreeLookup]);

  return (
    <Stack {...tree.getContainerProps()} className="tree" gap="0">
      {tree.getItems().map((item) => (
        <Box
          {...item.getProps()}
          key={item.getId()}
          ml={`${item.getItemMeta().level * 10}px`}
        >
          <TreeItem
            item={item}
            onCreateDir={handleCreateDir}
            onCreateFile={handleCreateEmptyFile}
            onDeleteFile={handleDeleteFile}
          />
        </Box>
      ))}
    </Stack>
  );
};
