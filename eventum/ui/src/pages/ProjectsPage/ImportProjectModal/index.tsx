import {
  Button,
  Group,
  Paper,
  Stack,
  Text,
  TextInput,
  ThemeIcon,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { modals } from '@mantine/modals';
import { IconFileZip, IconUpload } from '@tabler/icons-react';
import bytes from 'bytes';
import { FC, useRef, useState } from 'react';

import { projectNameFromArchive, validateProjectName } from '../project-name';
import { useImportGeneratorProjectMutation } from '@/api/hooks/useGeneratorConfigs';
import {
  showErrorNotification,
  showSuccessNotification,
} from '@/utils/notifications';

interface ImportProjectModalProps {
  existingProjectNames: string[];
  onImported?: (projectName: string) => void;
}

export const ImportProjectModal: FC<ImportProjectModalProps> = ({
  existingProjectNames,
  onImported,
}) => {
  const importProject = useImportGeneratorProjectMutation();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [archive, setArchive] = useState<File | null>(null);

  const form = useForm({
    initialValues: {
      projectName: '',
    },
    validate: {
      projectName: (value) => validateProjectName(value, existingProjectNames),
    },
    validateInputOnChange: true,
    onSubmitPreventDefault: 'always',
  });

  function handleArchiveSelected(files: FileList | null) {
    const selected = files?.[0];

    if (selected === undefined) return;

    setArchive(selected);

    // The archive name is a proposal, not a decision: an already typed
    // name is the user's and stays untouched.
    if (!form.isDirty('projectName')) {
      form.setFieldValue('projectName', projectNameFromArchive(selected.name));
    }
  }

  function handleImport() {
    if (archive === null) return;

    importProject.mutate(
      { name: form.values.projectName, archive },
      {
        onSuccess: () => {
          modals.closeAll();
          showSuccessNotification(
            'Imported',
            `Project "${form.values.projectName}" is imported`
          );
          onImported?.(form.values.projectName);
        },
        onError: (error) =>
          showErrorNotification('Failed to import project', error),
      }
    );
  }

  return (
    <form onSubmit={form.onSubmit(handleImport)}>
      <Stack>
        <Paper withBorder p="md">
          <Group justify="space-between" wrap="nowrap">
            <Group gap="sm" wrap="nowrap" style={{ minWidth: 0 }}>
              <ThemeIcon variant="default" size={38} radius="md">
                <IconFileZip size={20} stroke={1.5} />
              </ThemeIcon>
              <Stack gap={0} style={{ minWidth: 0 }}>
                <Text size="sm" fw={600} truncate>
                  {archive?.name ?? 'No archive selected'}
                </Text>
                <Text size="xs" c="dimmed">
                  {archive === null
                    ? 'ZIP archive of a project directory'
                    : bytes(archive.size)}
                </Text>
              </Stack>
            </Group>
            <Button
              variant="default"
              leftSection={<IconUpload size={16} />}
              onClick={() => fileInputRef.current?.click()}
            >
              {archive === null ? 'Choose' : 'Replace'}
            </Button>
          </Group>
        </Paper>

        <TextInput
          label="Project name"
          description="Name of the directory the archive is unpacked into"
          {...form.getInputProps('projectName')}
        />

        <Group justify="end">
          <Button
            loading={importProject.isPending}
            disabled={archive === null || !form.isValid()}
            type="submit"
          >
            Import
          </Button>
        </Group>
      </Stack>

      <input
        ref={fileInputRef}
        type="file"
        accept=".zip,application/zip"
        hidden
        onChange={(event) => {
          handleArchiveSelected(event.currentTarget.files);
          event.currentTarget.value = '';
        }}
      />
    </form>
  );
};
