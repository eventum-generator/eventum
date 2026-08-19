import { Button, Paper, Stack, Text, ThemeIcon } from '@mantine/core';
import { IconGitBranch } from '@tabler/icons-react';
import { FC } from 'react';

interface RepositoriesEmptyStateProps {
  onConnect: () => void;
}

/**
 * Shown when no repository is connected yet. Names what a connected
 * repository gives instead of an empty table.
 */
export const RepositoriesEmptyState: FC<RepositoriesEmptyStateProps> = ({
  onConnect,
}) => (
  <Paper withBorder p="xl">
    <Stack align="center" gap="sm" py="xl">
      <ThemeIcon variant="default" size={48} radius="md">
        <IconGitBranch size={24} stroke={1.5} />
      </ThemeIcon>
      <Text fw={600}>No repositories connected</Text>
      <Text size="sm" c="dimmed" ta="center" maw={460}>
        A connected repository publishes ready-to-use generators. Connect one to
        browse what it offers and install a generator as a project of this
        workspace.
      </Text>
      <Button mt="xs" onClick={onConnect}>
        Connect repository
      </Button>
    </Stack>
  </Paper>
);
