import { Button, Paper, Stack, Text, ThemeIcon } from '@mantine/core';
import { IconPlayerPlay } from '@tabler/icons-react';
import { FC } from 'react';

interface InstancesEmptyStateProps {
  onCreate: () => void;
}

/**
 * Shown when no instances are registered yet. Offers a single clear
 * action to create the first one instead of an empty table.
 */
export const InstancesEmptyState: FC<InstancesEmptyStateProps> = ({
  onCreate,
}) => (
  <Paper withBorder radius="md" p="xl">
    <Stack align="center" gap="sm" py="xl">
      <ThemeIcon variant="default" size={48} radius="md">
        <IconPlayerPlay size={24} stroke={1.5} />
      </ThemeIcon>
      <Text fw={600}>No instances yet</Text>
      <Text size="sm" c="dimmed" ta="center" maw={420}>
        An instance is a runnable generator built from a project. Create one to
        start producing events.
      </Text>
      <Button mt="xs" onClick={onCreate}>
        Create new instance
      </Button>
    </Stack>
  </Paper>
);
