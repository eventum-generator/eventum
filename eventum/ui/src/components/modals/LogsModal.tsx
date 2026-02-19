import { EditorState } from '@codemirror/state';
import { ActionIcon, Group, Stack, useMantineColorScheme } from '@mantine/core';
import { IconArrowBarToDown, IconArrowBarToUp } from '@tabler/icons-react';
import { vscodeDark, vscodeLight } from '@uiw/codemirror-theme-vscode';
import CodeMirror, { EditorView } from '@uiw/react-codemirror';
import { FC, useCallback, useEffect, useRef, useState } from 'react';

interface LogsModalProps {
  getWebSocket: () => WebSocket;
}

export const LogsModal: FC<LogsModalProps> = ({ getWebSocket }) => {
  const { colorScheme } = useMantineColorScheme();

  const [editorView, setEditorView] = useState<EditorView>();

  const appendLogs = useCallback(
    (chunk: string) => {
      if (!editorView) {
        return;
      }

      editorView.dispatch({
        changes: { from: editorView.state.doc.length, insert: chunk },
        scrollIntoView: false,
      });
    },
    [editorView]
  );

  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!editorView) {
      return;
    }

    const ws = getWebSocket();
    wsRef.current = ws;

    // eslint-disable-next-line unicorn/prefer-add-event-listener
    ws.onmessage = (event) => {
      appendLogs(String(event.data));
    };

    // eslint-disable-next-line unicorn/prefer-add-event-listener
    ws.onerror = () => {
      appendLogs('\n[Socket error]\n');
    };

    // eslint-disable-next-line unicorn/prefer-add-event-listener
    ws.onclose = (event) => {
      appendLogs(`\n[Socket has closed with code: ${event.code}]\n`);
    };

    return () => {
      ws.close(1000);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [editorView, appendLogs]);

  return (
    <Stack>
      <CodeMirror
        height="75vh"
        theme={colorScheme === 'dark' ? vscodeDark : vscodeLight}
        editable={false}
        extensions={[
          EditorView.lineWrapping,
          EditorState.readOnly.of(true),
          EditorView.editable.of(false),
          EditorView.contentAttributes.of({ tabindex: '0' }),
        ]}
        onCreateEditor={setEditorView}
      />

      <Group justify="end">
        <Group gap="xs">
          <ActionIcon
            title="Go to top"
            variant="default"
            size="lg"
            onClick={() => {
              if (editorView) {
                editorView.scrollDOM.scrollTo({ top: 0 });
              }
            }}
          >
            <IconArrowBarToUp size="20" />
          </ActionIcon>
          <ActionIcon
            title="Go to bottom"
            variant="default"
            size="lg"
            onClick={() => {
              if (editorView) {
                editorView.scrollDOM.scrollTo({
                  top: editorView.scrollDOM.scrollHeight,
                });
              }
            }}
          >
            <IconArrowBarToDown size="20" />
          </ActionIcon>
        </Group>
      </Group>
    </Stack>
  );
};
