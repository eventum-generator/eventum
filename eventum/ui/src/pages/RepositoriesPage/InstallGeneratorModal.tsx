import {
  Alert,
  Anchor,
  Button,
  Group,
  Stack,
  Text,
  TextInput,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { modals } from '@mantine/modals';
import { notifications } from '@mantine/notifications';
import { FC, useEffect } from 'react';

import { validateProjectName } from '../ProjectsPage/project-name';
import { proposeProjectName } from './project-name';
import { useInstallGeneratorMutation } from '@/api/hooks/useRepositories';
import { CatalogEntry } from '@/api/routes/repositories/schemas';
import { AlertIcon } from '@/components/ui/AlertIcon';
import { showErrorNotification } from '@/utils/notifications';

interface InstallGeneratorModalProps {
  repositoryName: string;
  entry: CatalogEntry;
  existingProjectNames: string[];
  /** Opens the project that was installed. Passed in rather than
   *  navigated to here: modal content is rendered outside the router. */
  onOpenProject: (projectName: string) => void;
}

export const InstallGeneratorModal: FC<InstallGeneratorModalProps> = ({
  repositoryName,
  entry,
  existingProjectNames,
  onOpenProject,
}) => {
  const installGenerator = useInstallGeneratorMutation();

  const form = useForm({
    initialValues: {
      projectName: proposeProjectName(entry.name, existingProjectNames),
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
                  onClick={() => onOpenProject(projectName)}
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

        {entry.installed_as.length > 0 && (
          <Alert variant="default" icon={<AlertIcon variant="info" />}>
            <Text size="sm">
              Already installed as{' '}
              {entry.installed_as.map((item) => item.project).join(', ')}.
              Installing writes another project; the one you have is left as it
              is.
            </Text>
          </Alert>
        )}
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
            {entry.installed_as.length > 0 ? 'Install again' : 'Install'}
          </Button>
        </Group>
      </Stack>
    </form>
  );
};
