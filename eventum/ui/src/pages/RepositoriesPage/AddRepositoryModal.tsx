import {
  Alert,
  Anchor,
  Button,
  Group,
  Select,
  Stack,
  Text,
  TextInput,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { modals } from '@mantine/modals';
import { FC, useState } from 'react';

import { describeAPIError } from '@/api/errorReport';
import { APIError } from '@/api/errors';
import { useAddRepositoryMutation } from '@/api/hooks/useRepositories';
import { useSecretNames } from '@/api/hooks/useSecrets';
import {
  REPOSITORY_NAME_PATTERN,
  REPOSITORY_REF_PATTERN,
} from '@/api/routes/repositories/schemas';
import { AlertIcon } from '@/components/ui/AlertIcon';
import {
  showErrorNotification,
  showSuccessNotification,
} from '@/utils/notifications';

// The status a repository that did not answer comes back with. Every
// other failure is the request itself being wrong, and retrying it
// unchecked would fail the same way.
const UNREACHABLE_STATUS = 502;

interface AddRepositoryModalProps {
  existingNames: string[];
  /** Opens the page secrets are managed on. Passed in rather than
   *  navigated to here: modal content is rendered outside the router. */
  onOpenSecrets: () => void;
  /** Name and address to open the form on, filled in when a
   *  repository of the published list is being connected. */
  prefilled?: { name: string; url: string };
}

export const AddRepositoryModal: FC<AddRepositoryModalProps> = ({
  existingNames,
  onOpenSecrets,
  prefilled,
}) => {
  const addRepository = useAddRepositoryMutation();
  const { data: secretNames } = useSecretNames();
  const [unreachable, setUnreachable] = useState<string | null>(null);

  const form = useForm({
    initialValues: {
      name: prefilled?.name ?? '',
      url: prefilled?.url ?? '',
      ref: '',
      username: '',
      secret: '',
    },
    validate: {
      name: (value) => {
        if (!value) return 'Name is required';
        if (!REPOSITORY_NAME_PATTERN.test(value)) {
          return 'Only letters, digits and symbols "-", "_" and "." are allowed';
        }
        if (existingNames.includes(value)) {
          return 'Repository with such name is already connected';
        }
        return null;
      },
      ref: (value) => {
        if (!value) return null;
        if (
          !REPOSITORY_REF_PATTERN.test(value) ||
          value.includes('..') ||
          value.endsWith('/') ||
          value.endsWith('.lock')
        ) {
          return 'Not a valid branch or tag name';
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

  function connect(verify: boolean) {
    setUnreachable(null);

    addRepository.mutate(
      {
        repository: {
          name: form.values.name,
          url: form.values.url,
          ref: form.values.ref || undefined,
          username: form.values.username || undefined,
          secret: form.values.secret || undefined,
        },
        verify,
      },
      {
        onSuccess: () => {
          modals.closeAll();
          showSuccessNotification(
            'Connected',
            `Repository "${form.values.name}" is connected`
          );
        },
        onError: (error) => {
          if (
            error instanceof APIError &&
            error.response?.status === UNREACHABLE_STATUS
          ) {
            setUnreachable(describeAPIError(error).reported);
            return;
          }

          showErrorNotification('Failed to connect repository', error);
        },
      }
    );
  }

  return (
    <form onSubmit={form.onSubmit(() => connect(true))}>
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
          placeholder="master"
          {...form.getInputProps('ref')}
        />
        <TextInput
          label="User name"
          description="Needed for a private repository"
          {...form.getInputProps('username')}
        />
        <Select
          label="Secret"
          description={
            <>
              For a private repository - the secret of the keyring holding its
              password or access token. Its name, not the value and not a{' '}
              <code>{'${secrets.*}'}</code> reference. Secrets are added on the{' '}
              <Anchor
                component="button"
                type="button"
                size="xs"
                onClick={() => {
                  modals.closeAll();
                  onOpenSecrets();
                }}
              >
                Secrets
              </Anchor>{' '}
              page.
            </>
          }
          data={secretNames ?? []}
          nothingFoundMessage="The keyring holds no secrets yet"
          searchable
          clearable
          {...form.getInputProps('secret')}
        />

        {unreachable !== null && (
          <Alert
            variant="default"
            icon={<AlertIcon variant="warn" />}
            title="The repository did not answer"
          >
            <Stack gap="xs" align="start">
              <Text size="sm">{unreachable}</Text>
              <Button
                variant="default"
                size="compact-sm"
                loading={addRepository.isPending}
                onClick={() => connect(false)}
              >
                Connect anyway
              </Button>
            </Stack>
          </Alert>
        )}

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
