import { Anchor, Button, Group, Stack, Text, TextInput } from '@mantine/core';
import { useForm } from '@mantine/form';
import { modals } from '@mantine/modals';
import { notifications } from '@mantine/notifications';
import { FC, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

import { validateProjectName } from '../ProjectsPage/project-name';
import { useInstallGeneratorMutation } from '@/api/hooks/useRepositories';
import { CatalogEntry } from '@/api/routes/repositories/schemas';
import { ROUTE_PATHS } from '@/routing/paths';
import { showErrorNotification } from '@/utils/notifications';

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
  const navigate = useNavigate();
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

  // The name arrives proposed rather than empty, so a name already
  // taken is stated at once instead of leaving a disabled button
  // without a reason.
  useEffect(() => {
    form.validate();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleInstall() {
    const projectName = form.values.projectName;

    installGenerator.mutate(
      {
        name: repositoryName,
        entry: entry.name,
        projectName,
      },
      {
        onSuccess: () => {
          modals.closeAll();
          notifications.show({
            title: 'Installed',
            message: (
              <>
                Generator is installed as &quot;{projectName}&quot;.{' '}
                <Anchor
                  component="button"
                  type="button"
                  size="sm"
                  onClick={() =>
                    void navigate(
                      ROUTE_PATHS.PROJECT.replace(':projectName', projectName)
                    )
                  }
                >
                  Open project
                </Anchor>
              </>
            ),
            color: 'green',
          });
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
