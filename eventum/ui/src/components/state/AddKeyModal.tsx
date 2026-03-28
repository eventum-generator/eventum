import {
  Button,
  Group,
  JsonInput,
  Modal,
  Stack,
  TextInput,
} from '@mantine/core';
import { useEffect, useState } from 'react';

export interface AddKeyModalProps {
  opened: boolean;
  onClose: () => void;
  existingKeys: string[];
  onAdd: (key: string, value: unknown) => void;
}

export function AddKeyModal({
  opened,
  onClose,
  existingKeys,
  onAdd,
}: Readonly<AddKeyModalProps>) {
  const [newKey, setNewKey] = useState('');
  const [jsonValue, setJsonValue] = useState('""');
  const [jsonError, setJsonError] = useState<string | null>(null);
  const [keyError, setKeyError] = useState<string | null>(null);

  useEffect(() => {
    if (opened) {
      setNewKey('');
      setJsonValue('""');
      setJsonError(null);
      setKeyError(null);
    }
  }, [opened]);

  function handleKeyChange(val: string) {
    setNewKey(val);
    if (!val.trim()) {
      setKeyError('Key is required');
    } else if (existingKeys.includes(val.trim())) {
      setKeyError('Key already exists');
    } else {
      setKeyError(null);
    }
  }

  function handleValueChange(val: string) {
    setJsonValue(val);
    try {
      JSON.parse(val);
      setJsonError(null);
    } catch {
      setJsonError('Invalid JSON');
    }
  }

  function handleAdd() {
    const key = newKey.trim();
    if (!key || existingKeys.includes(key)) return;

    try {
      const parsed = JSON.parse(jsonValue) as unknown;
      onAdd(key, parsed);
      onClose();
    } catch {
      setJsonError('Invalid JSON');
    }
  }

  return (
    <Modal opened={opened} onClose={onClose} title="Add key" size="md">
      <Stack gap="sm">
        <TextInput
          label="Key"
          placeholder="Enter key name..."
          value={newKey}
          onChange={(e) => handleKeyChange(e.currentTarget.value)}
          error={keyError}
          ff="monospace"
        />
        <JsonInput
          label="Value"
          value={jsonValue}
          onChange={handleValueChange}
          error={jsonError}
          placeholder="Enter JSON value..."
          minRows={3}
          autosize
          ff="monospace"
        />
        <Group justify="flex-end" gap="xs">
          <Button variant="default" onClick={onClose}>
            Cancel
          </Button>
          <Button
            onClick={handleAdd}
            disabled={!newKey.trim() || keyError !== null || jsonError !== null}
          >
            Add
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}
