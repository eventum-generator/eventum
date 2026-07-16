import {
  ActionIcon,
  Group,
  Loader,
  Table,
  Text,
  TextInput,
} from '@mantine/core';
import { isNotEmpty, useForm } from '@mantine/form';
import { useDisclosure } from '@mantine/hooks';
import { modals } from '@mantine/modals';
import { notifications } from '@mantine/notifications';
import {
  IconDeviceFloppy,
  IconEdit,
  IconEye,
  IconEyeOff,
  IconTrash,
  IconX,
} from '@tabler/icons-react';
import React, { FC, useState } from 'react';

import {
  useDeleteSecretValueMutation,
  useSecretValue,
  useSetSecretValueMutation,
} from '@/api/hooks/useSecrets';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';
import { CONFIRM } from '@/theme/copy';

interface TableRowProps {
  name: string;
}

const TableRow: FC<TableRowProps> = ({ name }) => {
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
      <Table.Td>{name}</Table.Td>
      <Table.Td>
        {isSecretValueLoading || isUpdatingValue ? (
          <Loader size="xs" />
        ) : isEditMode ? (
          <TextInput
            placeholder="secret value"
            {...form.getInputProps('value')}
          />
        ) : isValueShown ? (
          form.values.value
        ) : (
          '********'
        )}
      </Table.Td>
      <Table.Td style={{ verticalAlign: 'top' }}>
        <Group gap="xs" wrap="nowrap">
          <ActionIcon
            variant="transparent"
            title={isValueShown ? 'Hide' : 'Show'}
            size="lg"
            onClick={() => void handleOnValueVisibilityChange()}
            disabled={isEditMode}
          >
            {isValueShown ? <IconEyeOff size={20} /> : <IconEye size={20} />}
          </ActionIcon>

          <ActionIcon
            variant="transparent"
            title={isEditMode ? 'Save' : 'Edit'}
            size="lg"
            onClick={() => void handleOnEditModeChange(form.values)}
            disabled={
              isUpdatingValue || (form.initialized && !form.isValid('value'))
            }
          >
            {isEditMode ? (
              <IconDeviceFloppy size={20} />
            ) : (
              <IconEdit size={20} />
            )}
          </ActionIcon>

          <ActionIcon
            variant="transparent"
            c="var(--ev-bad)"
            title="Remove"
            size="lg"
            display={isEditMode ? 'none' : 'block'}
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
            <IconTrash size={20} stroke={1.5} />
          </ActionIcon>

          <ActionIcon
            variant="transparent"
            title="Cancel"
            size="lg"
            onClick={handleCancelEditing}
            display={isEditMode ? 'block' : 'none'}
          >
            <IconX size={20} />
          </ActionIcon>
        </Group>
      </Table.Td>
    </Table.Tr>
  );
};

export default React.memo(TableRow);
