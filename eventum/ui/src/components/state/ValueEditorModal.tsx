import { json, jsonParseLinter } from '@codemirror/lang-json';
import { linter } from '@codemirror/lint';
import { Button, Group, Modal, Stack, Text } from '@mantine/core';
import { useMantineColorScheme } from '@mantine/core';
import { IconEdit } from '@tabler/icons-react';
import { vscodeDark, vscodeLight } from '@uiw/codemirror-theme-vscode';
import CodeMirror from '@uiw/react-codemirror';
import { useEffect, useMemo, useState } from 'react';

export interface ValueEditorModalProps {
  opened: boolean;
  onClose: () => void;
  keyName: string;
  value: unknown;
  onSave: (key: string, value: unknown) => void;
}

export function ValueEditorModal({
  opened,
  onClose,
  keyName,
  value,
  onSave,
}: Readonly<ValueEditorModalProps>) {
  const { colorScheme } = useMantineColorScheme();
  const [jsonValue, setJsonValue] = useState('');
  const [jsonError, setJsonError] = useState<string | null>(null);

  const extensions = useMemo(() => [json(), linter(jsonParseLinter())], []);

  useEffect(() => {
    if (opened) {
      setJsonValue(JSON.stringify(value, undefined, 2));
      setJsonError(null);
    }
  }, [opened, value]);

  function handleChange(val: string) {
    setJsonValue(val);
    try {
      JSON.parse(val);
      setJsonError(null);
    } catch {
      setJsonError('Invalid JSON');
    }
  }

  function handleSave() {
    try {
      const parsed = JSON.parse(jsonValue) as unknown;
      onSave(keyName, parsed);
      onClose();
    } catch {
      setJsonError('Invalid JSON');
    }
  }

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={
        <Group gap="xs">
          <IconEdit size={16} />
          <Text fw={600} ff="monospace">
            {keyName}
          </Text>
        </Group>
      }
      size="80%"
    >
      <Stack gap="sm">
        <CodeMirror
          value={jsonValue}
          onChange={handleChange}
          extensions={extensions}
          theme={colorScheme === 'dark' ? vscodeDark : vscodeLight}
          height="75vh"
          basicSetup={{
            lineNumbers: true,
            foldGutter: true,
            bracketMatching: true,
            closeBrackets: true,
            indentOnInput: true,
          }}
        />
        {jsonError && (
          <Text size="sm" c="red">
            {jsonError}
          </Text>
        )}
        <Group justify="flex-end" gap="xs">
          <Button variant="default" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={jsonError !== null}>
            Save
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}
