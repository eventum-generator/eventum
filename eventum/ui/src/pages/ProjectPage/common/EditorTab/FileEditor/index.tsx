import { autocompletion } from '@codemirror/autocomplete';
import { jinja } from '@codemirror/lang-jinja';
import { json } from '@codemirror/lang-json';
import { markdown } from '@codemirror/lang-markdown';
import { python } from '@codemirror/lang-python';
import { yaml } from '@codemirror/lang-yaml';
import { keymap } from '@codemirror/view';
import { Alert, Box, Skeleton, useMantineColorScheme } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import CodeMirror from '@uiw/react-codemirror';
import bytes from 'bytes';
import { FC, useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';

import { SearchPanel } from './SearchPanel';
import { SearchPanelHandle, searchPanel } from './SearchPanel/extension';
import { jinjaCompletion } from './completions';
import {
  useGeneratorFileContent,
  useGeneratorFileTree,
  usePutGeneratorFileMutation,
} from '@/api/hooks/useGeneratorConfigs';
import { findFileNode } from '@/api/routes/generator-configs/modules/file-tree';
import { AlertIcon } from '@/components/ui/AlertIcon';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';
import { useProjectName } from '@/pages/ProjectPage/hooks/useProjectName';
import { cmTheme } from '@/theme/codemirror';

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

  // The search panel is a CodeMirror panel with a React body: the extension
  // hands over the element it mounted, the controls are rendered into it.
  const [searchHandle, setSearchHandle] = useState<SearchPanelHandle | null>(
    null
  );
  const searchExtension = useMemo(
    () =>
      searchPanel({
        onOpen: setSearchHandle,
        onClose: (closed) =>
          setSearchHandle((current) => (current === closed ? null : current)),
      }),
    []
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

  const saveKeymap = keymap.of([
    {
      key: 'Mod-s',
      preventDefault: true,
      run: () => {
        handleSave();
        return true;
      },
    },
  ]);

  const extensions = [];

  if (filePath.endsWith('.jinja')) {
    extensions.push(
      jinja(),
      autocompletion({
        override: [jinjaCompletion],
      })
    );
  } else if (filePath.endsWith('.py')) {
    extensions.push(python());
  } else if (filePath.endsWith('.json')) {
    extensions.push(json());
  } else if (/\.ya?ml$/.test(filePath)) {
    extensions.push(yaml());
  } else if (filePath.endsWith('.md')) {
    extensions.push(markdown());
  }

  extensions.push(saveKeymap, searchExtension);

  if (isTooLarge) {
    return (
      <Box p="md">
        <Alert
          variant="default"
          icon={<AlertIcon variant="warn" />}
          title="File is too large to open"
        >
          {bytes(fileSize)} exceeds the editor limit of{' '}
          {bytes(MAX_EDITABLE_SIZE)}. Open the file outside of Studio.
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
          onChange={(value) => {
            setContent(value);

            if (!isTouched) {
              setTouched(true);
            }
          }}
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
