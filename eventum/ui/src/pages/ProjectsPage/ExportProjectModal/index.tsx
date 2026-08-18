import {
  Alert,
  Button,
  Center,
  Checkbox,
  Group,
  Loader,
  Paper,
  ScrollArea,
  Stack,
  Text,
} from '@mantine/core';
import { modals } from '@mantine/modals';
import { IconFile, IconFolder } from '@tabler/icons-react';
import bytes from 'bytes';
import { FC, useState } from 'react';

import {
  useExportGeneratorProjectMutation,
  useGeneratorFileTree,
} from '@/api/hooks/useGeneratorConfigs';
import { useInstanceSettings } from '@/api/hooks/useInstance';
import { FileNode } from '@/api/routes/generator-configs/schemas';
import { AlertIcon } from '@/components/ui/AlertIcon';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';
import { downloadBlob } from '@/utils/download';
import { showErrorNotification } from '@/utils/notifications';

/** Size of a node with everything under it. */
function nodeSize(node: FileNode): number {
  if (!node.is_dir) return node.size_in_bytes ?? 0;

  return (node.children ?? []).reduce((sum, child) => sum + nodeSize(child), 0);
}

interface ExportProjectModalProps {
  projectName: string;
}

export const ExportProjectModal: FC<ExportProjectModalProps> = ({
  projectName,
}) => {
  const exportProject = useExportGeneratorProjectMutation();
  const [excluded, setExcluded] = useState<string[]>([]);

  const {
    data: fileTree,
    isLoading,
    isError,
    error,
  } = useGeneratorFileTree(projectName);

  const { data: instanceSettings } = useInstanceSettings();
  const configFilename =
    instanceSettings?.path.generator_config_filename ?? 'generator.yml';

  function handleExport() {
    exportProject.mutate(
      { name: projectName, exclude: excluded },
      {
        onSuccess: (archive) => {
          downloadBlob(archive, `${projectName}.zip`);
          modals.closeAll();
        },
        onError: (exportError) =>
          showErrorNotification('Failed to export project', exportError),
      }
    );
  }

  if (isLoading) {
    return (
      <Center py="xl">
        <Loader />
      </Center>
    );
  }

  if (isError) {
    return (
      <Alert
        variant="default"
        icon={<AlertIcon variant="error" />}
        title="Failed to load project files"
      >
        {error.message}
        <ShowErrorDetailsAnchor error={error} prependDot />
      </Alert>
    );
  }

  const entries = [...(fileTree ?? [])].sort((a, b) =>
    a.name.localeCompare(b.name)
  );
  const includedSize = entries
    .filter((entry) => !excluded.includes(entry.name))
    .reduce((sum, entry) => sum + nodeSize(entry), 0);

  return (
    <Stack>
      <Text size="sm" c="dimmed">
        The archive holds everything left ticked. Generated output is usually
        worth leaving out.
      </Text>

      <Paper withBorder>
        <ScrollArea.Autosize mah={280}>
          <Checkbox.Group
            value={entries
              .map((entry) => entry.name)
              .filter((name) => !excluded.includes(name))}
            onChange={(included) =>
              setExcluded(
                entries
                  .map((entry) => entry.name)
                  .filter((name) => !included.includes(name))
              )
            }
          >
            <Stack gap={0} p="xs">
              {entries.map((entry) => {
                const isConfig = !entry.is_dir && entry.name === configFilename;

                return (
                  <Group key={entry.name} justify="space-between" p="xs">
                    <Checkbox
                      value={entry.name}
                      disabled={isConfig}
                      label={
                        <Group gap="xs">
                          {entry.is_dir ? (
                            <IconFolder size={16} stroke={1.5} />
                          ) : (
                            <IconFile size={16} stroke={1.5} />
                          )}
                          <Text size="sm">{entry.name}</Text>
                        </Group>
                      }
                      description={
                        isConfig
                          ? 'Without it the archive cannot be imported'
                          : undefined
                      }
                    />
                    <Text size="sm" c="dimmed">
                      {bytes(nodeSize(entry))}
                    </Text>
                  </Group>
                );
              })}
            </Stack>
          </Checkbox.Group>
        </ScrollArea.Autosize>
      </Paper>

      <Group justify="space-between">
        <Text size="sm" c="dimmed">
          {bytes(includedSize)} before compression
        </Text>
        <Button loading={exportProject.isPending} onClick={handleExport}>
          Export
        </Button>
      </Group>
    </Stack>
  );
};
