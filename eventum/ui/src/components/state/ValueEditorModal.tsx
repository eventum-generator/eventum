import {
  Button,
  Group,
  JsonInput,
  Modal,
  Stack,
  Text,
} from '@mantine/core';
import { IconEdit } from '@tabler/icons-react';
import { useEffect, useState } from 'react';

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
  const [jsonValue, setJsonValue] = useState('');
  const [jsonError, setJsonError] = useState<string | null>(null);

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
      size="lg"
    >
      <Stack gap="sm">
        <JsonInput
          value={jsonValue}
          onChange={handleChange}
          error={jsonError}
          placeholder="Enter JSON value..."
          minRows={8}
          autosize
          maxRows={20}
          ff="monospace"
        />
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
