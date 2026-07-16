import { ItemInstance } from '@headless-tree/core';
import { ActionIcon, Box, Button, Center, Stack, Text } from '@mantine/core';
import { modals } from '@mantine/modals';
import { IconDeviceFloppy, IconPointFilled, IconX } from '@tabler/icons-react';
import { FC, useEffect, useMemo } from 'react';

import { FileEditor } from '../../common/EditorTab/FileEditor';
import { FileNodeItemIcon } from '../../common/FileTree/Tree/FileNodeItemIcon';
import { useStudioShell } from '../context';
import { useGeneratorFileTree } from '@/api/hooks/useGeneratorConfigs';
import { flattenFileTree } from '@/api/routes/generator-configs/modules/file-tree';
import { FileNode } from '@/api/routes/generator-configs/schemas';
import { CONFIRM } from '@/theme/copy';

const basename = (id: string): string => id.split('/').pop() ?? id;

interface OpenFileProps {
  item: ItemInstance<FileNode>;
  active: boolean;
}

const OpenFile: FC<OpenFileProps> = ({ item, active }) => {
  const { setSaved, registerSaver, unregisterSaver } = useStudioShell();
  const id = item.getId();

  useEffect(() => () => unregisterSaver(id), [id, unregisterSaver]);

  return (
    <Box className="studio-editor-file" hidden={!active}>
      <FileEditor
        filePath={id}
        height="100%"
        setSaved={(status) => setSaved(id, status)}
        registerSave={(save) => registerSaver(id, save)}
      />
    </Box>
  );
};

export const EditorPanel: FC = () => {
  const {
    projectName,
    openedItems,
    activeId,
    activateItem,
    closeItem,
    savedStatuses,
    saveFile,
  } = useStudioShell();

  const { data: fileTree, isSuccess } = useGeneratorFileTree(projectName);
  const existingIds = useMemo(
    () => (isSuccess ? flattenFileTree(fileTree, true) : []),
    [fileTree, isSuccess]
  );

  const activeDirty =
    activeId !== undefined && savedStatuses[activeId] === false;

  function requestClose(item: ItemInstance<FileNode>) {
    const id = item.getId();
    if (savedStatuses[id] === false && existingIds.includes(id)) {
      modals.openConfirmModal({
        title: CONFIRM.closeUnsavedFile.title,
        children: <Text size="sm">{CONFIRM.closeUnsavedFile.body(id)}</Text>,
        labels: {
          confirm: CONFIRM.closeUnsavedFile.confirm,
          cancel: CONFIRM.closeUnsavedFile.cancel,
        },
        onConfirm: () => closeItem(item),
      });
    } else {
      closeItem(item);
    }
  }

  return (
    <div className="studio-panel studio-editor">
      <div className="studio-panel-header">
        <span>Editor</span>
        {openedItems.length > 0 && (
          <Button
            size="compact-xs"
            variant="subtle"
            leftSection={<IconDeviceFloppy size={14} />}
            disabled={!activeDirty}
            onClick={() => activeId !== undefined && saveFile(activeId)}
          >
            Save file
          </Button>
        )}
      </div>

      {openedItems.length === 0 ? (
        <Center style={{ flex: 1 }} p="xl">
          <Stack gap={4} align="center" maw={320}>
            <Text size="sm" c="dimmed" ta="center">
              Select a file in the Explorer to open it here.
            </Text>
            <Text size="xs" c="dimmed" ta="center">
              Templates, samples and scripts open as tabs. Save with the button
              above or Ctrl/Cmd+S.
            </Text>
          </Stack>
        </Center>
      ) : (
        <>
          <div className="studio-tabstrip">
            {openedItems.map((item) => {
              const id = item.getId();
              const isActive = id === activeId;
              const isDirty = savedStatuses[id] === false;
              const missing = !existingIds.includes(id);
              return (
                <div
                  key={id}
                  className="studio-tab"
                  data-active={isActive}
                  title={id}
                >
                  <button
                    type="button"
                    className="studio-tab-btn"
                    onClick={() => activateItem(item)}
                  >
                    <FileNodeItemIcon item={item} />
                    <span className="studio-tab-name" data-missing={missing}>
                      {basename(id)}
                    </span>
                  </button>
                  {isDirty && <IconPointFilled size={12} />}
                  <ActionIcon
                    variant="subtle"
                    size="xs"
                    aria-label="Close file"
                    onClick={() => requestClose(item)}
                  >
                    <IconX size={13} />
                  </ActionIcon>
                </div>
              );
            })}
          </div>

          <div className="studio-editor-surface">
            {openedItems.map((item) => (
              <OpenFile
                key={item.getId()}
                item={item}
                active={item.getId() === activeId}
              />
            ))}
          </div>
        </>
      )}
    </div>
  );
};
