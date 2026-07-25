import { Button, Paper, Stack, Text, ThemeIcon } from '@mantine/core';
import { IconTransform } from '@tabler/icons-react';
import { FC } from 'react';

interface ScenariosEmptyStateProps {
  onCreate: () => void;
}

/**
 * Shown when no scenarios exist yet. Offers a single clear action to
 * create the first one instead of an empty table.
 */
export const ScenariosEmptyState: FC<ScenariosEmptyStateProps> = ({
  onCreate,
}) => (
  <Paper withBorder p="xl">
    <Stack align="center" gap="sm" py="xl">
      <ThemeIcon variant="default" size={48} radius="md">
        <IconTransform size={24} stroke={1.5} />
      </ThemeIcon>
      <Text fw={600}>No scenarios yet</Text>
      <Text size="sm" c="dimmed" ta="center" maw={420}>
        A scenario groups instances so you can start and stop them together.
        Create one to run related instances as a set.
      </Text>
      <Button mt="xs" onClick={onCreate}>
        Create new scenario
      </Button>
    </Stack>
  </Paper>
);
