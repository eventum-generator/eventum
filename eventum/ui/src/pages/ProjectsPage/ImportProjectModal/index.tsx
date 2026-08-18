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
import { DragEvent, FC, useRef, useState } from 'react';

import {
  projectNameFromArchive,
  projectNameFromDirectory,
  validateProjectName,
} from '../project-name';
import { projectRootName, readZipEntryNames } from './archive';
import { useImportGeneratorProjectMutation } from '@/api/hooks/useGeneratorConfigs';
import { useInstanceSettings } from '@/api/hooks/useInstance';
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
  const [isDragOver, setIsDragOver] = useState(false);

  // A name the user typed is theirs; only a proposed one is replaced
  // when another archive is selected.
  const [isNameEdited, setIsNameEdited] = useState(false);

  const { data: instanceSettings } = useInstanceSettings();
  const configFilename =
    instanceSettings?.path.generator_config_filename ?? 'generator.yml';

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

  /**
   * The directory the archive carries the project in names the project
   * better than the archive does - a `web-nginx.zip` downloaded as
   * `archive(1).zip` still imports as `web-nginx`. The file name is the
   * fallback, for an archive holding the project at its top level or
   * one that cannot be read here.
   */
  async function proposeName(file: File): Promise<string> {
    const root = projectRootName(await readZipEntryNames(file), configFilename);
    const fromRoot = root === null ? '' : projectNameFromDirectory(root);

    return fromRoot || projectNameFromArchive(file.name);
  }

  async function handleArchiveSelected(files: FileList | null) {
    const selected = files?.[0];

    if (selected === undefined) return;

    setArchive(selected);

    if (isNameEdited) return;

    form.setFieldValue('projectName', await proposeName(selected));
    form.validateField('projectName');
  }

  function handleDragOver(event: DragEvent<HTMLDivElement>) {
    if (!event.dataTransfer.types.includes('Files')) return;

    event.preventDefault();
    setIsDragOver(true);
  }

  function handleDragLeave(event: DragEvent<HTMLDivElement>) {
    if (event.currentTarget.contains(event.relatedTarget as Node | null)) {
      return;
    }

    setIsDragOver(false);
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setIsDragOver(false);
    void handleArchiveSelected(event.dataTransfer.files);
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
        <Paper
          withBorder
          p="md"
          onDragEnter={handleDragOver}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          style={{
            borderStyle: 'dashed',
            borderColor: isDragOver
              ? 'var(--mantine-primary-color-filled)'
              : undefined,
            backgroundColor: isDragOver
              ? 'var(--mantine-primary-color-light)'
              : undefined,
          }}
        >
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
                    ? 'Drop a ZIP archive of a project directory here'
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
          onChange={(event) => {
            setIsNameEdited(true);
            form.setFieldValue('projectName', event.currentTarget.value);
          }}
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
          void handleArchiveSelected(event.currentTarget.files);
          event.currentTarget.value = '';
        }}
      />
    </form>
  );
};
