import { Button, Group, Stack, Text, TextInput } from '@mantine/core';
import { useForm } from '@mantine/form';
import { modals } from '@mantine/modals';
import { FC } from 'react';

import { validateProjectName } from '../ProjectsPage/project-name';
import { useInstallGeneratorMutation } from '@/api/hooks/useRepositories';
import { CatalogEntry } from '@/api/routes/repositories/schemas';
import {
  showErrorNotification,
  showSuccessNotification,
} from '@/utils/notifications';

interface InstallGeneratorModalProps {
  repositoryName: string;
  entry: CatalogEntry;
  existingProjectNames: string[];
}

/** Fold everything a project name cannot hold into a single dash. */
function proposeName(entryName: string): string {
  return entryName.split(/\W/).filter(Boolean).join('-');
}

export const InstallGeneratorModal: FC<InstallGeneratorModalProps> = ({
  repositoryName,
  entry,
  existingProjectNames,
}) => {
  const installGenerator = useInstallGeneratorMutation();

  const form = useForm({
    initialValues: {
      projectName: proposeName(entry.name),
    },
    validate: {
      projectName: (value) => validateProjectName(value, existingProjectNames),
    },
    validateInputOnChange: true,
    onSubmitPreventDefault: 'always',
  });

  function handleInstall() {
    installGenerator.mutate(
      {
        name: repositoryName,
        entry: entry.name,
        projectName: form.values.projectName,
      },
      {
        onSuccess: () => {
          modals.closeAll();
          showSuccessNotification(
            'Installed',
            `Generator is installed as "${form.values.projectName}"`
          );
        },
        onError: (error) =>
          showErrorNotification('Failed to install generator', error),
      }
    );
  }

  return (
    <form onSubmit={form.onSubmit(handleInstall)}>
      <Stack>
        <Text size="sm" c="dimmed">
          {entry.title ?? entry.name}
        </Text>
        <TextInput
          label="Project name"
          description="Name of the directory the generator is installed into"
          {...form.getInputProps('projectName')}
        />
        <Group justify="end">
          <Button
            loading={installGenerator.isPending}
            disabled={!form.isValid()}
            type="submit"
          >
            Install
          </Button>
        </Group>
      </Stack>
    </form>
  );
};
