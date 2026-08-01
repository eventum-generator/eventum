import { ItemInstance } from '@headless-tree/core';
import { Box, Group, Kbd, NavLink, Text, TextInput } from '@mantine/core';
import { modals } from '@mantine/modals';
import {
  IconChevronDown,
  IconChevronRight,
  IconCursorText,
  IconFilePlus,
  IconFolderPlus,
  IconTrash,
} from '@tabler/icons-react';
import bytes from 'bytes';
import { useContextMenu } from 'mantine-contextmenu';
import { dirname, join } from 'pathe';
import { FC } from 'react';

import { CreateItemModal } from './CreateItemModal';
import { FileNodeItemIcon } from './FileNodeItemIcon';
import { useCreateGeneratorDirectoryMutation } from '@/api/hooks/useGeneratorConfigs';
import { FileNode } from '@/api/routes/generator-configs/schemas';
import { CONFIRM } from '@/theme/copy';

interface TreeItemProps {
  item: ItemInstance<FileNode>;
  // The root config file is required to open the project, so it must not be
  // renamed or deleted from the tree.
  isConfigFile?: boolean;
  onCreateDir: (dirpath: string) => void;
  onCreateFile: (filepath: string) => void;
  onDeleteFile: (filepath: string) => void;
}

export const TreeItem: FC<TreeItemProps> = ({
  item,
  isConfigFile = false,
  onCreateDir,
  onCreateFile,
  onDeleteFile,
}) => {
  'use no memo';

  const { showContextMenu } = useContextMenu();
  const createDir = useCreateGeneratorDirectoryMutation();

  const fileSize = item.isFolder() ? null : item.getItemData().size_in_bytes;

  return (
    <NavLink
      active={item.isSelected() || item.isDragTarget()}
      bdrs="6px"
      p="4px"
      onContextMenu={(ctxEvent) => {
        ctxEvent.stopPropagation();
        showContextMenu(
          [
            {
              key: 'new-file',
              title: (
                <NavLink
                  label="New file"
                  bdrs="6px"
                  p="1px 4px 1px 4px"
                  leftSection={<IconFilePlus size={16} />}
                />
              ),
              onClick: () =>
                modals.open({
                  title: 'Creating file',
                  children: (
                    <CreateItemModal
                      isLoading={createDir.isPending}
                      onCreate={(filepath) => {
                        let path = '';
                        if (item.isFolder()) {
                          path = join(item.getId(), filepath);
                        } else {
                          path = join(dirname(item.getId()), filepath);
                        }

                        onCreateFile(path);

                        modals.closeAll();
                      }}
                    />
                  ),
                }),
            },
            {
              key: 'new-folder',
              title: (
                <NavLink
                  label="New folder"
                  bdrs="6px"
                  p="1px 4px 1px 4px"
                  leftSection={<IconFolderPlus size={16} />}
                />
              ),
              onClick: () =>
                modals.open({
                  title: 'Creating directory',
                  children: (
                    <CreateItemModal
                      isLoading={createDir.isPending}
                      onCreate={(dirpath) => {
                        let path = '';
                        if (item.isFolder()) {
                          path = join(item.getId(), dirpath);
                        } else {
                          path = join(dirname(item.getId()), dirpath);
                        }

                        onCreateDir(path);

                        modals.closeAll();
                      }}
                    />
                  ),
                }),
            },
            // The config file cannot be renamed or deleted from the tree.
            ...(isConfigFile
              ? []
              : [
                  {
                    key: 'rename',
                    title: (
                      <NavLink
                        label="Rename"
                        bdrs="6px"
                        p="1px 4px 1px 4px"
                        leftSection={<IconCursorText size={16} />}
                        rightSection={<Kbd size="xs">F2</Kbd>}
                      />
                    ),
                    onClick: item.startRenaming,
                  },
                  {
                    key: 'delete',
                    title: (
                      <NavLink
                        label="Delete"
                        bdrs="6px"
                        p="1px 4px 1px 4px"
                        leftSection={<IconTrash size={16} />}
                        rightSection={<Kbd size="xs">Del</Kbd>}
                      />
                    ),
                    onClick: () => {
                      modals.openConfirmModal({
                        title: CONFIRM.deleteFile.title,
                        children: (
                          <Text size="sm">
                            {CONFIRM.deleteFile.body(item.getId())}
                          </Text>
                        ),
                        labels: {
                          confirm: CONFIRM.deleteFile.confirm,
                          cancel: CONFIRM.deleteFile.cancel,
                        },
                        onConfirm: () => onDeleteFile(item.getId()),
                      });
                    },
                  },
                ]),
          ],
          {
            styles: {
              root: { borderRadius: '8px', padding: '6px', width: '200px' },
            },
          }
        )(ctxEvent);
      }}
      label={
        <Group wrap="nowrap" gap="6px" align="center">
          {item.isFolder() ? (
            <Group wrap="nowrap" gap="2px">
              {item.isExpanded() ? (
                <IconChevronDown size={15} />
              ) : (
                <IconChevronRight size={15} />
              )}

              <FileNodeItemIcon item={item} />
            </Group>
          ) : (
            <Box ml="16px">
              <FileNodeItemIcon item={item} />
            </Box>
          )}
          {item.isRenaming() ? (
            <TextInput
              {...item.getRenameInputProps()}
              size="sm"
              styles={{
                input: {
                  minHeight: 'unset',
                  height: '20px',
                  padding: '0',
                  borderRadius: '4px',
                },
              }}
            />
          ) : (
            // A long name is cut with an ellipsis rather than wrapped onto a
            // second line, so every row keeps one height; the full name stays
            // reachable on hover.
            <Text
              size="sm"
              truncate="end"
              title={item.getItemName()}
              style={{ minWidth: 0 }}
            >
              {item.getItemName()}
            </Text>
          )}
          {fileSize !== null && !item.isRenaming() && (
            // Metadata: the smallest step of the type scale, dimmed, and
            // rounded to whole units - the exact byte count is not what the
            // reader is scanning the tree for.
            <Text fz={11} c="dimmed" ml="auto" style={{ flexShrink: 0 }}>
              {bytes(fileSize, { decimalPlaces: 0 })}
            </Text>
          )}
        </Group>
      }
    />
  );
};
