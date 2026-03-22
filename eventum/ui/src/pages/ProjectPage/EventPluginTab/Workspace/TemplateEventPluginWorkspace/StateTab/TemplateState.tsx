import {
  ActionIcon,
  Alert,
  Badge,
  Box,
  Button,
  Group,
  JsonInput,
  Menu,
  Modal,
  Pagination,
  Skeleton,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
  Tooltip,
} from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { modals } from '@mantine/modals';
import { notifications } from '@mantine/notifications';
import {
  IconAlertSquareRounded,
  IconDotsVertical,
  IconEdit,
  IconEraser,
  IconPencil,
  IconPlus,
  IconRefresh,
  IconSearch,
  IconTrash,
} from '@tabler/icons-react';
import { FC, useCallback, useEffect, useMemo, useState } from 'react';

import {
  useClearTemplateEventPluginGlobalStateMutation,
  useClearTemplateEventPluginLocalStateMutation,
  useClearTemplateEventPluginSharedStateMutation,
  useTemplateEventPluginGlobalState,
  useTemplateEventPluginLocalState,
  useTemplateEventPluginSharedState,
  useUpdateTemplateEventPluginGlobalStateMutation,
  useUpdateTemplateEventPluginLocalStateMutation,
  useUpdateTemplateEventPluginSharedStateMutation,
} from '@/api/hooks/usePreview';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';
import { useProjectName } from '@/pages/ProjectPage/hooks/useProjectName';

const PAGE_SIZE = 20;

function getValueType(value: unknown): string {
  if (value === null) return 'null';
  if (Array.isArray(value)) return 'array';
  return typeof value;
}

function formatValuePreview(value: unknown): string {
  if (value === null) return 'null';
  if (value === undefined) return 'undefined';

  const type = typeof value;
  if (type === 'string') return `"${value}"`;
  if (type === 'number' || type === 'boolean') return String(value);

  if (Array.isArray(value)) {
    return `[${value.length} items]`;
  }

  if (type === 'object') {
    const keys = Object.keys(value as object);
    return `{${keys.length} keys}`;
  }

  return String(value);
}

function isSimpleValue(value: unknown): boolean {
  if (value === null || value === undefined) return true;
  const type = typeof value;
  return type === 'string' || type === 'number' || type === 'boolean';
}

function typeBadgeColor(type: string): string {
  switch (type) {
    case 'string':
      return 'green';
    case 'number':
      return 'blue';
    case 'boolean':
      return 'orange';
    case 'object':
      return 'violet';
    case 'array':
      return 'cyan';
    case 'null':
      return 'gray';
    default:
      return 'gray';
  }
}

interface ValueEditorModalProps {
  opened: boolean;
  onClose: () => void;
  keyName: string;
  value: unknown;
  onSave: (key: string, value: unknown) => void;
}

function ValueEditorModal({
  opened,
  onClose,
  keyName,
  value,
  onSave,
}: ValueEditorModalProps) {
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

interface AddKeyModalProps {
  opened: boolean;
  onClose: () => void;
  existingKeys: string[];
  onAdd: (key: string, value: unknown) => void;
}

function AddKeyModal({
  opened,
  onClose,
  existingKeys,
  onAdd,
}: AddKeyModalProps) {
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

export interface TemplateStateProps {
  stateName: string;
  templateAlias: string;
  useTemplateEventPluginState:
    | typeof useTemplateEventPluginLocalState
    | typeof useTemplateEventPluginSharedState
    | typeof useTemplateEventPluginGlobalState;
  useUpdateTemplateEventPluginStateMutation:
    | typeof useUpdateTemplateEventPluginLocalStateMutation
    | typeof useUpdateTemplateEventPluginSharedStateMutation
    | typeof useUpdateTemplateEventPluginGlobalStateMutation;
  useClearTemplateEventPluginStateMutation:
    | typeof useClearTemplateEventPluginLocalStateMutation
    | typeof useClearTemplateEventPluginSharedStateMutation
    | typeof useClearTemplateEventPluginGlobalStateMutation;
}

export const TemplateState: FC<TemplateStateProps> = ({
  stateName,
  templateAlias,
  useTemplateEventPluginState,
  useUpdateTemplateEventPluginStateMutation,
  useClearTemplateEventPluginStateMutation,
}) => {
  const { projectName } = useProjectName();
  const { data, isLoading, isError, error, isSuccess, refetch } =
    useTemplateEventPluginState(projectName, templateAlias);

  const updateState = useUpdateTemplateEventPluginStateMutation();
  const clearState = useClearTemplateEventPluginStateMutation();

  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [editingValue, setEditingValue] = useState<unknown>(null);
  const [editorOpened, editorHandlers] = useDisclosure(false);
  const [addOpened, addHandlers] = useDisclosure(false);
  const [inlineEditKey, setInlineEditKey] = useState<string | null>(null);
  const [inlineEditValue, setInlineEditValue] = useState('');

  const entries = useMemo(() => {
    if (!data) return [];
    return Object.entries(data).sort(([a], [b]) => a.localeCompare(b));
  }, [data]);

  const filteredEntries = useMemo(() => {
    if (!search.trim()) return entries;
    const q = search.toLowerCase();
    return entries.filter(
      ([key, value]) =>
        key.toLowerCase().includes(q) ||
        formatValuePreview(value).toLowerCase().includes(q),
    );
  }, [entries, search]);

  const totalPages = Math.max(
    1,
    Math.ceil(filteredEntries.length / PAGE_SIZE),
  );
  const currentPage = Math.min(page, totalPages);

  const pageEntries = useMemo(
    () =>
      filteredEntries.slice(
        (currentPage - 1) * PAGE_SIZE,
        currentPage * PAGE_SIZE,
      ),
    [filteredEntries, currentPage],
  );

  const existingKeys = useMemo(() => entries.map(([key]) => key), [entries]);

  const handleUpdateKey = useCallback(
    (key: string, value: unknown) => {
      if (!data) return;
      const newState = { ...data, [key]: value };
      updateState.mutate(
        { name: projectName, templateAlias, state: newState } as never,
        {
          onSuccess: () => {
            notifications.show({
              title: 'Updated',
              message: `Key "${key}" updated`,
              color: 'green',
            });
          },
          onError: (updateError: Error) => {
            notifications.show({
              title: 'Error',
              message: (
                <>
                  Failed to update key
                  <ShowErrorDetailsAnchor error={updateError} prependDot />
                </>
              ),
              color: 'red',
            });
          },
        },
      );
    },
    [data, updateState, projectName, templateAlias],
  );

  const handleDeleteKey = useCallback(
    (key: string) => {
      modals.openConfirmModal({
        title: 'Delete key',
        children: (
          <Text size="sm">
            Delete key <b>{key}</b> from {stateName.toLowerCase()}?
          </Text>
        ),
        labels: { cancel: 'Cancel', confirm: 'Delete' },
        confirmProps: { color: 'red' },
        onConfirm: () => {
          if (!data) return;
          const newState = { ...data };
          delete newState[key];
          updateState.mutate(
            { name: projectName, templateAlias, state: newState } as never,
            {
              onSuccess: () => {
                notifications.show({
                  title: 'Deleted',
                  message: `Key "${key}" removed`,
                  color: 'green',
                });
              },
              onError: (deleteError: Error) => {
                notifications.show({
                  title: 'Error',
                  message: (
                    <>
                      Failed to delete key
                      <ShowErrorDetailsAnchor error={deleteError} prependDot />
                    </>
                  ),
                  color: 'red',
                });
              },
            },
          );
        },
      });
    },
    [data, updateState, projectName, templateAlias, stateName],
  );

  const handleAddKey = useCallback(
    (key: string, value: unknown) => {
      if (!data) return;
      const newState = { ...data, [key]: value };
      updateState.mutate(
        { name: projectName, templateAlias, state: newState } as never,
        {
          onSuccess: () => {
            notifications.show({
              title: 'Added',
              message: `Key "${key}" added`,
              color: 'green',
            });
          },
          onError: (addError: Error) => {
            notifications.show({
              title: 'Error',
              message: (
                <>
                  Failed to add key
                  <ShowErrorDetailsAnchor error={addError} prependDot />
                </>
              ),
              color: 'red',
            });
          },
        },
      );
    },
    [data, updateState, projectName, templateAlias],
  );

  function handleClear() {
    modals.openConfirmModal({
      title: `Clear ${stateName.toLowerCase()}`,
      children: (
        <Text size="sm">
          This will remove all {entries.length} keys from{' '}
          {stateName.toLowerCase()}. This action cannot be undone.
        </Text>
      ),
      labels: { cancel: 'Cancel', confirm: 'Clear all' },
      confirmProps: { color: 'red' },
      onConfirm: () => {
        clearState.mutate(
          { name: projectName, templateAlias } as never,
          {
            onSuccess: () => {
              notifications.show({
                title: 'Cleared',
                message: `${stateName} cleared`,
                color: 'green',
              });
            },
            onError: (clearError: Error) => {
              notifications.show({
                title: 'Error',
                message: (
                  <>
                    Failed to clear state
                    <ShowErrorDetailsAnchor error={clearError} prependDot />
                  </>
                ),
                color: 'red',
              });
            },
          },
        );
      },
    });
  }

  function openEditor(key: string, value: unknown) {
    setEditingKey(key);
    setEditingValue(value);
    editorHandlers.open();
  }

  function startInlineEdit(key: string, value: unknown) {
    setInlineEditKey(key);
    setInlineEditValue(String(value));
  }

  function commitInlineEdit(key: string, originalValue: unknown) {
    const type = typeof originalValue;
    let parsed: unknown;

    if (type === 'number') {
      parsed = Number(inlineEditValue);
      if (Number.isNaN(parsed as number)) {
        setInlineEditKey(null);
        return;
      }
    } else if (type === 'boolean') {
      parsed = inlineEditValue === 'true';
    } else {
      parsed = inlineEditValue;
    }

    if (parsed !== originalValue) {
      handleUpdateKey(key, parsed);
    }
    setInlineEditKey(null);
  }

  function handleEditClick(key: string, value: unknown) {
    if (isSimpleValue(value) && value !== null) {
      startInlineEdit(key, value);
    } else {
      openEditor(key, value);
    }
  }

  return (
    <Stack gap="xs">
      <Group justify="space-between" align="center">
        <Group gap="xs">
          <Title order={6} fw={600}>
            {stateName}
          </Title>
          {isSuccess && (
            <Badge variant="light" size="xs">
              {entries.length} key{entries.length !== 1 ? 's' : ''}
            </Badge>
          )}
        </Group>
        <Group gap="xs">
          <Tooltip label="Refresh">
            <ActionIcon
              variant="default"
              size="sm"
              onClick={() => void refetch()}
              loading={isLoading}
            >
              <IconRefresh size={14} />
            </ActionIcon>
          </Tooltip>
          <Tooltip label="Add key">
            <ActionIcon
              variant="default"
              size="sm"
              onClick={addHandlers.open}
              disabled={!isSuccess}
            >
              <IconPlus size={14} />
            </ActionIcon>
          </Tooltip>
          <Tooltip label="Clear all">
            <ActionIcon
              variant="default"
              size="sm"
              onClick={handleClear}
              disabled={!isSuccess || entries.length === 0}
              loading={clearState.isPending}
            >
              <IconEraser size={14} />
            </ActionIcon>
          </Tooltip>
        </Group>
      </Group>

      {isLoading && <Skeleton h="120px" />}

      {isError && (
        <Alert
          variant="default"
          icon={<Box c="red" component={IconAlertSquareRounded} />}
          title="Failed to load state, ensure debugger is started"
        >
          {error.message}
          <ShowErrorDetailsAnchor error={error} prependDot />
        </Alert>
      )}

      {isSuccess && entries.length === 0 && (
        <Text size="sm" c="dimmed" ta="center" py="sm">
          No keys
        </Text>
      )}

      {isSuccess && entries.length > 0 && (
        <>
          <TextInput
            placeholder="Search keys or values..."
            leftSection={<IconSearch size={14} />}
            value={search}
            onChange={(e) => {
              setSearch(e.currentTarget.value);
              setPage(1);
            }}
            size="xs"
          />

          <Table.ScrollContainer minWidth={0}>
            <Table striped highlightOnHover verticalSpacing={4} fz="sm">
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Key</Table.Th>
                  <Table.Th>Value</Table.Th>
                  <Table.Th w={40} />
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {pageEntries.map(([key, value]) => {
                  const valueType = getValueType(value);

                  return (
                    <Table.Tr key={key}>
                      <Table.Td style={{ maxWidth: 140 }}>
                        <Text size="sm" ff="monospace" truncate>
                          {key}
                        </Text>
                      </Table.Td>
                      <Table.Td style={{ maxWidth: 180 }}>
                        {inlineEditKey === key ? (
                          <TextInput
                            size="xs"
                            ff="monospace"
                            value={inlineEditValue}
                            onChange={(e) =>
                              setInlineEditValue(e.currentTarget.value)
                            }
                            onBlur={() => commitInlineEdit(key, value)}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter')
                                commitInlineEdit(key, value);
                              if (e.key === 'Escape') setInlineEditKey(null);
                            }}
                            // eslint-disable-next-line jsx-a11y/no-autofocus -- intentional for inline edit UX
                            autoFocus
                          />
                        ) : (
                          <Group gap={6} wrap="nowrap">
                            <Badge
                              size="xs"
                              variant="light"
                              color={typeBadgeColor(valueType)}
                              style={{ flexShrink: 0 }}
                            >
                              {valueType}
                            </Badge>
                            <Text
                              size="sm"
                              ff="monospace"
                              truncate
                              c="dimmed"
                              style={{ cursor: 'pointer' }}
                              onClick={() => handleEditClick(key, value)}
                            >
                              {formatValuePreview(value)}
                            </Text>
                          </Group>
                        )}
                      </Table.Td>
                      <Table.Td>
                        <Menu position="bottom-end" withinPortal>
                          <Menu.Target>
                            <ActionIcon variant="subtle" size="sm">
                              <IconDotsVertical size={14} />
                            </ActionIcon>
                          </Menu.Target>
                          <Menu.Dropdown>
                            <Menu.Item
                              leftSection={<IconPencil size={14} />}
                              onClick={() => handleEditClick(key, value)}
                            >
                              Edit
                            </Menu.Item>
                            <Menu.Item
                              leftSection={<IconEdit size={14} />}
                              onClick={() => openEditor(key, value)}
                            >
                              Edit as JSON
                            </Menu.Item>
                            <Menu.Divider />
                            <Menu.Item
                              leftSection={<IconTrash size={14} />}
                              color="red"
                              onClick={() => handleDeleteKey(key)}
                            >
                              Delete
                            </Menu.Item>
                          </Menu.Dropdown>
                        </Menu>
                      </Table.Td>
                    </Table.Tr>
                  );
                })}
              </Table.Tbody>
            </Table>
          </Table.ScrollContainer>

          {totalPages > 1 && (
            <Group justify="space-between" align="center">
              <Text size="xs" c="dimmed">
                {filteredEntries.length} of {entries.length} keys
              </Text>
              <Pagination
                size="xs"
                total={totalPages}
                value={currentPage}
                onChange={setPage}
              />
            </Group>
          )}
        </>
      )}

      {editingKey && (
        <ValueEditorModal
          opened={editorOpened}
          onClose={() => {
            editorHandlers.close();
            setEditingKey(null);
          }}
          keyName={editingKey}
          value={editingValue}
          onSave={handleUpdateKey}
        />
      )}

      <AddKeyModal
        opened={addOpened}
        onClose={addHandlers.close}
        existingKeys={existingKeys}
        onAdd={handleAddKey}
      />
    </Stack>
  );
};
