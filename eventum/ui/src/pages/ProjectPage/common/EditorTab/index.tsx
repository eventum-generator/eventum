import { ItemInstance } from '@headless-tree/core';
import {
  ActionIcon,
  Alert,
  Box,
  Center,
  Divider,
  Flex,
  Group,
  ScrollArea,
  SegmentedControl,
  Skeleton,
  Stack,
  Text,
} from '@mantine/core';
import { modals } from '@mantine/modals';
import {
  IconAlertSquareRounded,
  IconPointFilled,
  IconX,
} from '@tabler/icons-react';
import { FC, useEffect, useMemo, useState } from 'react';

import { useProjectName } from '../../hooks/useProjectName';
import { FileNodeItemIcon } from '../FileTree/Tree/FileNodeItemIcon';
import { FileEditor } from './FileEditor';
import { useGeneratorFileTree } from '@/api/hooks/useGeneratorConfigs';
import { flattenFileTree } from '@/api/routes/generator-configs/modules/file-tree';
import { FileNode } from '@/api/routes/generator-configs/schemas';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';
import { useFileTree } from '@/pages/ProjectPage/hooks/useFileTree';

export const EditorTab: FC = () => {
  const [openedItems, setOpenedItems] = useState<ItemInstance<FileNode>[]>([]);
  const { selectedItem, setSelectedItem } = useFileTree();

  useEffect(() => {
    if (selectedItem !== undefined && !selectedItem.isFolder()) {
      setOpenedItems((prev) => {
        // check if file is not already opened
        for (const item of prev) {
          if (item.getId() === selectedItem.getId()) {
            return [...prev];
          }
        }

        return [...prev, selectedItem];
      });
    }
  }, [selectedItem]);

  const [savedStatuses, setSavedStatuses] = useState<Record<string, boolean>>(
    {}
  );

  const { projectName } = useProjectName();
  const {
    data: fileTree,
    isLoading: isFileTreeLoading,
    isError: isFileTreeError,
    error: fileTreeError,
    isSuccess: isFileTreeSuccess,
  } = useGeneratorFileTree(projectName);

  const filesList = useMemo(() => {
    if (isFileTreeSuccess) {
      return flattenFileTree(fileTree, true);
    } else {
      return [];
    }
  }, [fileTree, isFileTreeSuccess]);

  function handleOnChangeSelectedItem(newItemId: string) {
    let item: ItemInstance<FileNode> | undefined;
    if (selectedItem !== undefined) {
      item = selectedItem.getTree().getItemInstance(newItemId);
    } else if (openedItems.length > 0) {
      item = openedItems[0]!.getTree().getItemInstance(newItemId);
    }

    if (item === undefined || item.getId() === selectedItem?.getId()) {
      return;
    }

    setSelectedItem(item);
  }

  function handleCloseFile(item: ItemInstance<FileNode>) {
    const itemId = item.getId();

    const index = openedItems.findIndex(
      (openedItem) => openedItem.getId() === itemId
    );

    if (index === -1) {
      return;
    }

    setOpenedItems((prev) => {
      return [...prev.slice(0, index), ...prev.slice(index + 1)];
    });

    if (itemId === selectedItem?.getId()) {
      if (index === 0) {
        setSelectedItem(openedItems[1]);
      } else {
        setSelectedItem(openedItems[index - 1]);
      }
    }

    setSavedStatuses((prev) => {
      const newStatuses = { ...prev };
      delete newStatuses[itemId];
      return newStatuses;
    });
  }

  return (
    <Stack>
      {isFileTreeLoading && (
        <Stack>
          <Skeleton h="450px" animate visible />
        </Stack>
      )}

      {isFileTreeError && (
        <Alert
          variant="default"
          icon={<Box c="red" component={IconAlertSquareRounded}></Box>}
          title="Failed to load list of project files"
        >
          {fileTreeError.message}
          <ShowErrorDetailsAnchor error={fileTreeError} prependDot />
        </Alert>
      )}

      {isFileTreeSuccess && (
        <Stack>
          {openedItems.length > 0 ? (
            <Stack gap="4px">
              <ScrollArea type="hover" offsetScrollbars="x" scrollbarSize="5px">
                <SegmentedControl
                  data={openedItems.map((item) => ({
                    label: (
                      <Center>
                        <Group gap="4px" wrap="nowrap">
                          <FileNodeItemIcon item={item} />
                          <span>
                            {filesList.includes(item.getId()) ? (
                              item.getId()
                            ) : (
                              <Box title="Not exists">
                                <s>{item.getId()}</s>
                              </Box>
                            )}
                          </span>
                          {item.getId() in savedStatuses &&
                            !savedStatuses[item.getId()] && (
                              <Flex title="Unsaved" align="center">
                                <IconPointFilled size={20} />
                              </Flex>
                            )}
                          <ActionIcon
                            variant="subtle"
                            size="sm"
                            bdrs="sm"
                            onClick={() => {
                              if (
                                item.getId() in savedStatuses &&
                                !savedStatuses[item.getId()] &&
                                filesList.includes(item.getId())
                              ) {
                                modals.openConfirmModal({
                                  title: 'Unsaved changes',
                                  children: (
                                    <Text size="sm">
                                      All unsaved changes in{' '}
                                      <b>{item.getId()}</b> will be lost. Do you
                                      want to continue?
                                    </Text>
                                  ),
                                  labels: {
                                    confirm: 'Confirm',
                                    cancel: 'Cancel',
                                  },
                                  onConfirm: () => {
                                    handleCloseFile(item);
                                  },
                                });
                              } else {
                                handleCloseFile(item);
                              }
                            }}
                          >
                            <IconX size={16} />
                          </ActionIcon>
                        </Group>
                      </Center>
                    ),
                    value: item.getId(),
                  }))}
                  value={selectedItem?.getId()}
                  onChange={handleOnChangeSelectedItem}
                />
              </ScrollArea>
              {selectedItem !== undefined && !selectedItem.isFolder() ? (
                openedItems.map((item) => (
                  <Box
                    key={item.getId()}
                    hidden={item.getId() !== selectedItem.getId()}
                  >
                    <FileEditor
                      filePath={item.getId()}
                      setSaved={(status) => {
                        setSavedStatuses((prev) => {
                          const id = item.getId();
                          return { ...prev, [id]: status };
                        });
                      }}
                    />
                  </Box>
                ))
              ) : (
                <Stack>
                  <Divider />
                  <Center>
                    <Text size="sm" c="gray.6">
                      No file selected
                    </Text>
                  </Center>
                </Stack>
              )}
            </Stack>
          ) : (
            <Center>
              <Text size="sm" c="gray.6">
                No files
              </Text>
            </Center>
          )}
        </Stack>
      )}
    </Stack>
  );
};
