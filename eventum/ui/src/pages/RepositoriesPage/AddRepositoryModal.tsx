import { Button, Group, Select, Stack, TextInput } from '@mantine/core';
import { useForm } from '@mantine/form';
import { modals } from '@mantine/modals';
import { FC } from 'react';

import { useAddRepositoryMutation } from '@/api/hooks/useRepositories';
import { useSecretNames } from '@/api/hooks/useSecrets';
import {
  showErrorNotification,
  showSuccessNotification,
} from '@/utils/notifications';

const NAME_PATTERN = /^[a-zA-Z0-9](?:[a-zA-Z0-9._-]*[a-zA-Z0-9])?$/;

interface AddRepositoryModalProps {
  existingNames: string[];
}

export const AddRepositoryModal: FC<AddRepositoryModalProps> = ({
  existingNames,
}) => {
  const addRepository = useAddRepositoryMutation();
  const { data: secretNames } = useSecretNames();

  const form = useForm({
    initialValues: {
      name: '',
      url: '',
      ref: '',
      username: '',
      secret: '',
    },
    validate: {
      name: (value) => {
        if (!value) return 'Name is required';
        if (!NAME_PATTERN.test(value)) {
          return 'Only letters, digits and symbols "-", "_" and "." are allowed';
        }
        if (existingNames.includes(value)) {
          return 'Repository with such name is already connected';
        }
        return null;
      },
      url: (value) => {
        if (!value) return 'URL is required';
        if (!/^https?:\/\/.+/.test(value)) {
          return 'URL must start with "http://" or "https://"';
        }
        if (/^https?:\/\/[^/]*@/.test(value)) {
          return 'Provide credentials as user name and secret, not in the URL';
        }
        return null;
      },
    },
    validateInputOnChange: true,
    onSubmitPreventDefault: 'always',
  });

  function handleAdd() {
    addRepository.mutate(
      {
        name: form.values.name,
        url: form.values.url,
        ref: form.values.ref || undefined,
        username: form.values.username || undefined,
        secret: form.values.secret || undefined,
      },
      {
        onSuccess: () => {
          modals.closeAll();
          showSuccessNotification(
            'Connected',
            `Repository "${form.values.name}" is connected`
          );
        },
        onError: (error) =>
          showErrorNotification('Failed to connect repository', error),
      }
    );
  }

  return (
    <form onSubmit={form.onSubmit(handleAdd)}>
      <Stack>
        <TextInput
          label="Name"
          description="Name the repository is referred to by"
          {...form.getInputProps('name')}
        />
        <TextInput
          label="URL"
          description="Address the repository is fetched from"
          placeholder="https://github.com/eventum-generator/content-packs.git"
          {...form.getInputProps('url')}
        />
        <TextInput
          label="Branch or tag"
          description="Left empty, the default branch is fetched"
          {...form.getInputProps('ref')}
        />
        <TextInput
          label="User name"
          description="Needed for a private repository"
          {...form.getInputProps('username')}
        />
        <Select
          label="Secret"
          description="Keyring secret holding the password or access token"
          data={secretNames ?? []}
          searchable
          clearable
          {...form.getInputProps('secret')}
        />

        <Group justify="end">
          <Button
            loading={addRepository.isPending}
            disabled={!form.isValid()}
            type="submit"
          >
            Connect
          </Button>
        </Group>
      </Stack>
    </form>
  );
};
