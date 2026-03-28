import {
  ActionIcon,
  Alert,
  Badge,
  Box,
  Group,
  Menu,
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
import {
  IconAlertSquareRounded,
  IconAlertTriangle,
  IconDotsVertical,
  IconEdit,
  IconEraser,
  IconPencil,
  IconPlus,
  IconRefresh,
  IconSearch,
  IconTrash,
} from '@tabler/icons-react';
import { ReactNode, useCallback, useMemo, useState } from 'react';

import { AddKeyModal } from './AddKeyModal';
import { ValueEditorModal } from './ValueEditorModal';
import {
  formatValuePreview,
  getValueType,
  isSimpleValue,
  typeBadgeColor,
} from './value-helpers';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';

const PAGE_SIZE = 20;

export interface KeyValueTableProps {
  data: Record<string, unknown> | undefined;
  isLoading: boolean;
  isError: boolean;
  error: Error | null;
  isSuccess: boolean;
  onRefetch: () => void;
  onUpdateKey: (key: string, value: unknown) => void;
  onDeleteKey: (key: string) => void;
  onAddKey: (key: string, value: unknown) => void;
  onClear: () => void;
  title: string;
  titleIcon?: ReactNode;
  titleOrder?: 5 | 6;
  isClearPending?: boolean;
  emptyMessage?: string;
  errorTitle?: string;
  warningTitle?: string;
  warningMessage?: string;
  compact?: boolean;
}

export function KeyValueTable({
  data,
  isLoading,
  isError,
  error,
  isSuccess,
  onRefetch,
  onUpdateKey,
  onDeleteKey,
  onAddKey,
  onClear,
  title,
  titleIcon,
  titleOrder = 5,
  isClearPending = false,
  emptyMessage = 'No keys',
  errorTitle = 'Failed to load state',
  warningTitle,
  warningMessage,
  compact = false,
}: Readonly<KeyValueTableProps>) {
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [editingValue, setEditingValue] = useState<unknown>(null);
  const [editorOpened, editorHandlers] = useDisclosure(false);
  const [addOpened, addHandlers] = useDisclosure(false);
  const [inlineEditKey, setInlineEditKey] = useState<string | null>(null);
  const [inlineEditValue, setInlineEditValue] = useState('');

  const badgeSize = compact ? 'xs' : 'sm';
  const actionIconSize = 'lg';
  const actionIconInnerSize = compact ? 16 : 18;
  const skeletonHeight = compact ? '120px' : '200px';
  const keyMaxWidth = compact ? 140 : 160;
  const valueMaxWidth = compact ? 180 : 200;

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
        formatValuePreview(value).toLowerCase().includes(q)
    );
  }, [entries, search]);

  const totalPages = Math.max(1, Math.ceil(filteredEntries.length / PAGE_SIZE));
  const currentPage = Math.min(page, totalPages);

  const pageEntries = useMemo(
    () =>
      filteredEntries.slice(
        (currentPage - 1) * PAGE_SIZE,
        currentPage * PAGE_SIZE
      ),
    [filteredEntries, currentPage]
  );

  const existingKeys = useMemo(() => entries.map(([key]) => key), [entries]);

  const handleDeleteKey = useCallback(
    (key: string) => {
      modals.openConfirmModal({
        title: 'Delete key',
        children: (
          <Text size="sm">
            Delete key <b>{key}</b> from {title.toLowerCase()}?
          </Text>
        ),
        labels: { cancel: 'Cancel', confirm: 'Delete' },
        confirmProps: { color: 'red' },
        onConfirm: () => {
          onDeleteKey(key);
        },
      });
    },
    [onDeleteKey, title]
  );

  const handleClear = useCallback(() => {
    modals.openConfirmModal({
      title: `Clear ${title.toLowerCase()}`,
      children: (
        <Text size="sm">
          This will remove all {entries.length} keys from {title.toLowerCase()}.
          This action cannot be undone.
        </Text>
      ),
      labels: { cancel: 'Cancel', confirm: 'Clear all' },
      confirmProps: { color: 'red' },
      onConfirm: () => {
        onClear();
      },
    });
  }, [title, entries.length, onClear]);

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
      onUpdateKey(key, parsed);
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
    <>
      <Stack gap={compact ? 'xs' : 'sm'}>
        <Group justify="space-between" align="center">
          <Group gap="xs">
            {titleIcon}
            <Title order={titleOrder} fw={compact ? 600 : 'normal'}>
              {title}
            </Title>
            {isSuccess && (
              <Badge variant="light" size={badgeSize}>
                {entries.length} key{entries.length !== 1 ? 's' : ''}
              </Badge>
            )}
          </Group>
          <Group gap="xs">
            <Tooltip label="Refresh">
              <ActionIcon
                variant="default"
                size={actionIconSize}
                onClick={onRefetch}
                loading={isLoading}
              >
                <IconRefresh size={actionIconInnerSize} />
              </ActionIcon>
            </Tooltip>
            <Tooltip label="Add key">
              <ActionIcon
                variant="default"
                size={actionIconSize}
                onClick={addHandlers.open}
                disabled={!isSuccess}
              >
                <IconPlus size={actionIconInnerSize} />
              </ActionIcon>
            </Tooltip>
            <Tooltip label="Clear all">
              <ActionIcon
                variant="default"
                size={actionIconSize}
                onClick={handleClear}
                disabled={!isSuccess || entries.length === 0}
                loading={isClearPending}
              >
                <IconEraser size={actionIconInnerSize} />
              </ActionIcon>
            </Tooltip>
          </Group>
        </Group>

        {isLoading && <Skeleton h={skeletonHeight} />}

        {isError && (
          <Alert
            variant="default"
            icon={<Box c="red" component={IconAlertSquareRounded} />}
            title={errorTitle}
          >
            {error?.message}
            {error && <ShowErrorDetailsAnchor error={error} prependDot />}
          </Alert>
        )}

        {isSuccess && entries.length === 0 && (
          <Text size="sm" c="dimmed" ta="center" py={compact ? 'sm' : 'md'}>
            {emptyMessage}
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
                        <Table.Td style={{ maxWidth: keyMaxWidth }}>
                          <Text size="sm" ff="monospace" truncate>
                            {key}
                          </Text>
                        </Table.Td>
                        <Table.Td style={{ maxWidth: valueMaxWidth }}>
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
                                td="underline"
                                style={{
                                  cursor: 'pointer',
                                  textDecorationStyle: 'dotted',
                                }}
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
                              <ActionIcon
                                variant="transparent"
                                size="sm"
                                aria-label="Key actions"
                              >
                                <IconDotsVertical size={14} />
                              </ActionIcon>
                            </Menu.Target>
                            <Menu.Dropdown>
                              {isSimpleValue(value) && value !== null && (
                                <Menu.Item
                                  leftSection={<IconPencil size={14} />}
                                  onClick={() => startInlineEdit(key, value)}
                                >
                                  Edit
                                </Menu.Item>
                              )}
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

        {warningTitle && warningMessage && (
          <Alert
            variant="default"
            icon={<Box c="orange" component={IconAlertTriangle} />}
            title={warningTitle}
            p={compact ? 'xs' : undefined}
          >
            <Text size={compact ? 'xs' : 'sm'}>{warningMessage}</Text>
          </Alert>
        )}
      </Stack>

      {editingKey && (
        <ValueEditorModal
          opened={editorOpened}
          onClose={() => {
            editorHandlers.close();
            setEditingKey(null);
          }}
          keyName={editingKey}
          value={editingValue}
          onSave={onUpdateKey}
        />
      )}

      <AddKeyModal
        opened={addOpened}
        onClose={addHandlers.close}
        existingKeys={existingKeys}
        onAdd={onAddKey}
      />
    </>
  );
}
