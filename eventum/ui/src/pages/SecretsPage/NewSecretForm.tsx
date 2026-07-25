import { Button, Group, Paper, PasswordInput, TextInput } from '@mantine/core';
import { isNotEmpty, useForm } from '@mantine/form';
import { notifications } from '@mantine/notifications';
import { FC } from 'react';

import { useSetSecretValueMutation } from '@/api/hooks/useSecrets';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';

interface NewSecretFormProps {
  /** Close the form without adding anything. */
  onCancel: () => void;
}

/**
 * Inline form for adding a secret to the keyring. Lives above the list
 * instead of inside the table so its fields lay out cleanly. Stays open
 * after a successful add (fields reset) to make entering several in a row
 * quick; the caller closes it via `onCancel`.
 */
export const NewSecretForm: FC<NewSecretFormProps> = ({ onCancel }) => {
  const form = useForm<{ name: string; value: string }>({
    initialValues: {
      name: '',
      value: '',
    },
    validate: {
      name: isNotEmpty('Name is required'),
      value: isNotEmpty('Value is required'),
    },
    validateInputOnChange: true,
    onSubmitPreventDefault: 'always',
  });

  const setSecret = useSetSecretValueMutation();

  function handleSubmit(values: typeof form.values) {
    setSecret.mutate(
      { name: values.name, value: values.value },
      {
        onError: (error) => {
          notifications.show({
            title: 'Error',
            message: (
              <>
                Failed to add new secret.{' '}
                <ShowErrorDetailsAnchor error={error} />
              </>
            ),
            color: 'red',
          });
        },
        onSuccess: () => {
          form.reset();
          notifications.show({
            title: 'Success',
            message: 'New secret was added',
            color: 'green',
          });
        },
      }
    );
  }

  function handleCancel() {
    form.reset();
    onCancel();
  }

  return (
    <Paper withBorder shadow="none" p="md" bg="var(--mantine-color-gray-light)">
      <form onSubmit={form.onSubmit(handleSubmit)}>
        <Group align="flex-end" gap="sm" wrap="nowrap">
          <TextInput
            label="Name"
            placeholder="new-secret-name"
            style={{ flex: 1 }}
            data-autofocus
            {...form.getInputProps('name')}
          />
          <PasswordInput
            label="Value"
            placeholder="secret value"
            style={{ flex: 1 }}
            {...form.getInputProps('value')}
          />
          <Button
            type="submit"
            disabled={!form.isValid()}
            loading={setSecret.isPending}
          >
            Add
          </Button>
          <Button variant="default" onClick={handleCancel}>
            Cancel
          </Button>
        </Group>
      </form>
    </Paper>
  );
};
