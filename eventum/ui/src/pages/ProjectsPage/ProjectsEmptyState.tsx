import { Button, Group, Paper, Stack, Text, ThemeIcon } from '@mantine/core';
import { IconFolderPlus } from '@tabler/icons-react';
import { FC } from 'react';

interface ProjectsEmptyStateProps {
  onCreate: () => void;
  onImport: () => void;
}

/**
 * Shown when the workspace has no projects yet. Offers a single clear
 * action to create the first one instead of an empty table.
 */
export const ProjectsEmptyState: FC<ProjectsEmptyStateProps> = ({
  onCreate,
  onImport,
}) => (
  <Paper withBorder p="xl">
    <Stack align="center" gap="sm" py="xl">
      <ThemeIcon variant="default" size={48} radius="md">
        <IconFolderPlus size={24} stroke={1.5} />
      </ThemeIcon>
      <Text fw={600}>No projects yet</Text>
      <Text size="sm" c="dimmed" ta="center" maw={420}>
        A project holds the configuration, templates, and sample data for one
        generator. Create one to start producing events, or import one packed
        elsewhere.
      </Text>
      <Group mt="xs">
        <Button variant="default" onClick={onImport}>
          Import project
        </Button>
        <Button onClick={onCreate}>Create new project</Button>
      </Group>
    </Stack>
  </Paper>
);
