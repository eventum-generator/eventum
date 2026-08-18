import { keymap } from '@codemirror/view';
import {
  Alert,
  Box,
  Button,
  Group,
  Skeleton,
  useMantineColorScheme,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconDownload } from '@tabler/icons-react';
import CodeMirror from '@uiw/react-codemirror';
import bytes from 'bytes';
import { basename } from 'pathe';
import { FC, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';

import { SearchPanel } from './SearchPanel';
import { SearchPanelHandle, searchPanel } from './SearchPanel/extension';
import { languageExtensions } from './language';
import {
  useGeneratorFileContent,
  useGeneratorFileTree,
  usePutGeneratorFileMutation,
} from '@/api/hooks/useGeneratorConfigs';
import { getGeneratorFileDownloadUrl } from '@/api/routes/generator-configs';
import { findFileNode } from '@/api/routes/generator-configs/modules/file-tree';
import { AlertIcon } from '@/components/ui/AlertIcon';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';
import { useProjectName } from '@/pages/ProjectPage/hooks/useProjectName';
import { cmTheme } from '@/theme/codemirror';
import { downloadUrl } from '@/utils/download';

// Files above this size are not requested at all: transferring one takes
// as long as the link needs, and the editor cannot usefully display it.
// Generator output files are the usual case - they grow without a bound.
const MAX_EDITABLE_SIZE = 10 * 1024 * 1024;

export interface FileEditorProps {
  filePath: string;
  setSaved: (saved: boolean) => void;
  height?: string;
  registerSave?: (save: () => void) => void;
}

export const FileEditor: FC<FileEditorProps> = ({
  filePath,
  setSaved,
  height = '65vh',
  registerSave,
}) => {
  const { colorScheme } = useMantineColorScheme();
  const { projectName } = useProjectName();

  // The file tree carries the size of every file, so an oversized file is
  // recognized before its content is requested. Until the tree resolves
  // the size is unknown and the request waits.
  const { data: fileTree, isPending: isFileTreePending } =
    useGeneratorFileTree(projectName);
  const fileSize =
    fileTree === undefined
      ? null
      : (findFileNode(fileTree, filePath)?.size_in_bytes ?? null);
  const isTooLarge = fileSize !== null && fileSize > MAX_EDITABLE_SIZE;

  const {
    data: fileContent,
    isLoading: isContentLoading,
    isError: isContentError,
    error: contentError,
    isSuccess: isContentSuccess,
  } = useGeneratorFileContent(projectName, filePath, {
    enabled: !isFileTreePending && !isTooLarge,
  });
  const updateFile = usePutGeneratorFileMutation();

  const [content, setContent] = useState<string>('');
  const [isTouched, setTouched] = useState(false);

  const [searchHandle, setSearchHandle] = useState<SearchPanelHandle | null>(
    null
  );

  useEffect(() => {
    if (isContentSuccess) {
      setContent(fileContent);
      setTouched(false);
    }
  }, [fileContent, isContentSuccess]);

  useEffect(() => {
    if (isTouched) {
      setSaved(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isTouched]);

  function handleSave() {
    updateFile.mutate(
      { name: projectName, filepath: filePath, content: content },
      {
        onSuccess: () => {
          setSaved(true);
          setTouched(false);
        },
        onError: (error) => {
          notifications.show({
            title: 'Error',
            message: (
              <>
                Failed to save file
                <ShowErrorDetailsAnchor error={error} prependDot />
              </>
            ),
            color: 'red',
          });
        },
      }
    );
  }

  // Expose the current save to the studio (visible Save button, Save all).
  const saveRef = useRef(handleSave);
  saveRef.current = handleSave;
  useEffect(() => {
    registerSave?.(() => saveRef.current());
  }, [registerSave]);

  // The editor rebuilds its whole configuration whenever this array or the
  // change handler changes identity, so both stay stable while the file is
  // edited. The keymap goes through the save ref for the same reason: the
  // save closes over the content and is rebuilt on every keystroke.
  const extensions = useMemo(
    () => [
      ...languageExtensions(filePath),
      keymap.of([
        {
          key: 'Mod-s',
          preventDefault: true,
          run: () => {
            saveRef.current();
            return true;
          },
        },
      ]),
      // The search panel is a CodeMirror panel with a React body: the
      // extension hands over the element it mounted, the controls are
      // rendered into it.
      searchPanel({
        onOpen: setSearchHandle,
        onClose: (closed) =>
          setSearchHandle((current) => (current === closed ? null : current)),
      }),
    ],
    [filePath]
  );

  const handleChange = useCallback((value: string) => {
    setContent(value);
    setTouched(true);
  }, []);

  if (isTooLarge) {
    return (
      <Box p="md">
        <Alert
          variant="default"
          icon={<AlertIcon variant="warn" />}
          title="File is too large to open"
        >
          <Group justify="space-between" wrap="nowrap" gap="md">
            <span>
              {bytes(fileSize)} exceeds the editor limit of{' '}
              {bytes(MAX_EDITABLE_SIZE)}.
            </span>
            <Button
              variant="default"
              size="xs"
              leftSection={<IconDownload size={16} />}
              style={{ flexShrink: 0 }}
              onClick={() =>
                downloadUrl(
                  getGeneratorFileDownloadUrl(projectName, filePath),
                  basename(filePath)
                )
              }
            >
              Download
            </Button>
          </Group>
        </Alert>
      </Box>
    );
  }

  if (isFileTreePending || isContentLoading) {
    return <Skeleton h={height} />;
  }

  if (isContentError) {
    return (
      <Box p="md">
        <Alert
          variant="default"
          icon={<AlertIcon variant="error" />}
          title="Failed to load file content"
        >
          {contentError.message}
          <ShowErrorDetailsAnchor error={contentError} prependDot />
        </Alert>
      </Box>
    );
  }

  if (isContentSuccess) {
    return (
      <>
        <CodeMirror
          value={content}
          onChange={handleChange}
          height={height}
          extensions={extensions}
          theme={cmTheme(colorScheme)}
        />
        {searchHandle &&
          createPortal(<SearchPanel handle={searchHandle} />, searchHandle.dom)}
      </>
    );
  }

  return null;
};
