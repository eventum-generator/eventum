import {
  ActionIcon,
  CopyButton,
  Group,
  Loader,
  PasswordInput,
  Table,
  Text,
  Tooltip,
} from '@mantine/core';
import { isNotEmpty, useForm } from '@mantine/form';
import { useDisclosure } from '@mantine/hooks';
import { modals } from '@mantine/modals';
import { notifications } from '@mantine/notifications';
import {
  IconCheck,
  IconCopy,
  IconCursorText,
  IconDeviceFloppy,
  IconEdit,
  IconEye,
  IconEyeOff,
  IconTrash,
  IconX,
} from '@tabler/icons-react';
import React, { FC, useState } from 'react';

import { RenameSecretModal } from './RenameSecretModal';
import {
  useDeleteSecretValueMutation,
  useSecretValue,
  useSetSecretValueMutation,
} from '@/api/hooks/useSecrets';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';
import { CONFIRM } from '@/theme/copy';

interface SecretRowProps {
  name: string;
  existingNames: string[];
}

/** Fixed-length mask so a hidden value never leaks its real length. */
const MaskedValue: FC = () => (
  <Text ff="monospace" c="dimmed" style={{ letterSpacing: 2 }}>
    {'•'.repeat(8)}
  </Text>
);

const SecretRow: FC<SecretRowProps> = ({ name, existingNames }) => {
  const [isValueShown, { open: showValue, close: hideValue }] =
    useDisclosure(false);
  const [isEditMode, setEditMode] = useState(false);
  const [isUpdatingValue, setUpdatingValue] = useState(false);

  const {
    data: secretValue,
    refetch: fetchSecretValue,
    isLoading: isSecretValueLoading,
  } = useSecretValue(name);

  const updateSecretValue = useSetSecretValueMutation();
  const deleteSecretValue = useDeleteSecretValueMutation();

  const form = useForm<{ value: string }>({
    validate: {
      value: isNotEmpty('Value is required'),
    },
    validateInputOnChange: true,
    onSubmitPreventDefault: 'always',
  });

  function notifyAboutFetchError(error: unknown) {
    notifications.show({
      title: 'Error',
      message: (
        <>
          Failed to get secret value. <ShowErrorDetailsAnchor error={error} />
        </>
      ),
      color: 'red',
    });
  }

  async function handleOnValueVisibilityChange() {
    if (isValueShown) {
      hideValue();
    } else {
      if (!form.initialized) {
        const { data, error, isSuccess } = await fetchSecretValue();

        if (isSuccess) {
          form.initialize({ value: data });
          showValue();
        } else {
          notifyAboutFetchError(error);
        }
      } else {
        showValue();
      }
    }
  }

  async function handleOnEditModeChange(values: typeof form.values) {
    if (isEditMode) {
      setUpdatingValue(true);
      updateSecretValue.mutate(
        { name: name, value: values.value },
        {
          onError: (error) => {
            setUpdatingValue(false);
            notifications.show({
              title: 'Error',
              message: (
                <>
                  Failed to update secret value.{' '}
                  <ShowErrorDetailsAnchor error={error} />
                </>
              ),
              color: 'red',
            });
          },
          onSuccess: () => {
            setEditMode(false);
            setUpdatingValue(false);
            notifications.show({
              title: 'Success',
              message: 'Secret value was updated',
              color: 'green',
            });
          },
        }
      );
    } else {
      if (!form.initialized) {
        const { data, error, isSuccess } = await fetchSecretValue();

        if (isSuccess) {
          form.initialize({ value: data });
          setEditMode(true);
        } else {
          notifyAboutFetchError(error);
        }
      } else {
        setEditMode(true);
      }
    }
  }

  function handleCancelEditing() {
    setEditMode(false);
    form.setFieldValue('value', secretValue ?? '');
  }

  function handleRename() {
    modals.open({
      title: 'Rename secret',
      children: (
        <RenameSecretModal
          secretName={name}
          existingSecretNames={existingNames}
        />
      ),
      size: 'md',
    });
  }

  function handleDelete() {
    deleteSecretValue.mutate(
      { name: name },
      {
        onSuccess: () => {
          notifications.show({
            title: 'Success',
            message: 'Secret was deleted',
            color: 'green',
          });
        },
        onError: (error) => {
          notifications.show({
            title: 'Error',
            message: (
              <>
                Failed to delete secret.{' '}
                <ShowErrorDetailsAnchor error={error} />
              </>
            ),
            color: 'red',
          });
        },
      }
    );
  }

  return (
    <Table.Tr>
      <Table.Td>
        <Group gap={6} wrap="nowrap">
          <Text ff="monospace" size="sm">
            {name}
          </Text>
          <CopyButton value={name} timeout={1500}>
            {({ copied, copy }) => (
              <Tooltip
                label={copied ? 'Copied' : 'Copy name'}
                withArrow
                position="right"
              >
                <ActionIcon
                  className="ev-copy-btn"
                  variant="subtle"
                  size="sm"
                  onClick={copy}
                  aria-label="Copy secret name"
                >
                  {copied ? (
                    <IconCheck
                      size={14}
                      color="var(--mantine-color-green-text)"
                    />
                  ) : (
                    <IconCopy size={14} color="var(--mantine-color-text)" />
                  )}
                </ActionIcon>
              </Tooltip>
            )}
          </CopyButton>
          <Tooltip label="Rename" withArrow position="right">
            <ActionIcon
              className="ev-copy-btn"
              variant="subtle"
              size="sm"
              onClick={handleRename}
              aria-label="Rename secret"
            >
              <IconCursorText size={14} color="var(--mantine-color-text)" />
            </ActionIcon>
          </Tooltip>
        </Group>
      </Table.Td>
      <Table.Td>
        {isSecretValueLoading || isUpdatingValue ? (
          <Loader size="xs" />
        ) : isEditMode ? (
          <PasswordInput
            placeholder="secret value"
            {...form.getInputProps('value')}
          />
        ) : isValueShown ? (
          <Text ff="monospace" size="sm" style={{ wordBreak: 'break-all' }}>
            {form.values.value}
          </Text>
        ) : (
          <MaskedValue />
        )}
      </Table.Td>
      <Table.Td style={{ verticalAlign: 'middle' }}>
        <Group gap={4} wrap="nowrap" justify="flex-end">
          <ActionIcon
            variant="subtle"
            title={isValueShown ? 'Hide' : 'Show'}
            size="md"
            onClick={() => void handleOnValueVisibilityChange()}
            display={isEditMode ? 'none' : undefined}
          >
            {isValueShown ? (
              <IconEyeOff size={18} color="var(--mantine-color-text)" />
            ) : (
              <IconEye size={18} color="var(--mantine-color-text)" />
            )}
          </ActionIcon>

          <ActionIcon
            variant="subtle"
            title={isEditMode ? 'Save' : 'Edit'}
            size="md"
            onClick={() => void handleOnEditModeChange(form.values)}
            disabled={
              isUpdatingValue || (form.initialized && !form.isValid('value'))
            }
          >
            {isEditMode ? (
              <IconDeviceFloppy
                size={18}
                color="var(--mantine-color-primary-text)"
              />
            ) : (
              <IconEdit size={18} color="var(--mantine-color-text)" />
            )}
          </ActionIcon>

          <ActionIcon
            variant="subtle"
            title="Remove"
            size="md"
            display={isEditMode ? 'none' : undefined}
            onClick={() => {
              modals.openConfirmModal({
                title: CONFIRM.deleteSecret.title,
                children: (
                  <Text size="sm">{CONFIRM.deleteSecret.body(name)}</Text>
                ),
                onConfirm: handleDelete,
                labels: {
                  cancel: CONFIRM.deleteSecret.cancel,
                  confirm: CONFIRM.deleteSecret.confirm,
                },
              });
            }}
          >
            <IconTrash
              size={18}
              stroke={1.5}
              color="var(--mantine-color-red-text)"
            />
          </ActionIcon>

          <ActionIcon
            variant="subtle"
            title="Cancel"
            size="md"
            onClick={handleCancelEditing}
            display={isEditMode ? undefined : 'none'}
          >
            <IconX size={18} color="var(--mantine-color-text)" />
          </ActionIcon>
        </Group>
      </Table.Td>
    </Table.Tr>
  );
};

export default React.memo(SecretRow);
