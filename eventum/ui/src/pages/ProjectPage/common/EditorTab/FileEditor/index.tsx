import { autocompletion } from '@codemirror/autocomplete';
import { jinja } from '@codemirror/lang-jinja';
import { json } from '@codemirror/lang-json';
import { markdown } from '@codemirror/lang-markdown';
import { python } from '@codemirror/lang-python';
import { yaml } from '@codemirror/lang-yaml';
import { keymap } from '@codemirror/view';
import {
  Alert,
  Box,
  Skeleton,
  Stack,
  useMantineColorScheme,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconAlertSquareRounded } from '@tabler/icons-react';
import { vscodeDark, vscodeLight } from '@uiw/codemirror-theme-vscode';
import CodeMirror from '@uiw/react-codemirror';
import { FC, useEffect, useState } from 'react';

import { jinjaCompletion } from './completions';
import {
  useGeneratorFileContent,
  usePutGeneratorFileMutation,
} from '@/api/hooks/useGeneratorConfigs';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';
import { useProjectName } from '@/pages/ProjectPage/hooks/useProjectName';

export interface FileEditorProps {
  filePath: string;
  setSaved: (saved: boolean) => void;
}

export const FileEditor: FC<FileEditorProps> = ({ filePath, setSaved }) => {
  const { colorScheme } = useMantineColorScheme();
  const { projectName } = useProjectName();
  const {
    data: fileContent,
    isLoading: isContentLoading,
    isError: isContentError,
    error: contentError,
    isSuccess: isContentSuccess,
  } = useGeneratorFileContent(projectName, filePath);
  const updateFile = usePutGeneratorFileMutation();

  const [content, setContent] = useState<string>('');
  const [isTouched, setTouched] = useState(false);

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

  extensions.push(saveKeymap);

  if (isContentLoading) {
    return <Skeleton h="60vh" />;
  }

  if (isContentError) {
    return (
      <Alert
        variant="default"
        icon={<Box c="red" component={IconAlertSquareRounded}></Box>}
        title="Failed to load file content"
      >
        {contentError.message}
        <ShowErrorDetailsAnchor error={contentError} prependDot />
      </Alert>
    );
  }

  if (isContentSuccess) {
    return (
      <Stack gap="xs">
        <CodeMirror
          value={content}
          onChange={(value) => {
            setContent(value);

            if (!isTouched) {
              setTouched(true);
            }
          }}
          height="65vh"
          extensions={extensions}
          theme={colorScheme === 'dark' ? vscodeDark : vscodeLight}
        />
      </Stack>
    );
  }

  return null;
};
