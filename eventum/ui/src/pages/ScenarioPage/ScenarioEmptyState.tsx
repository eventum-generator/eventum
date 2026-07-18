import { Button, Paper, Stack, Text, ThemeIcon } from '@mantine/core';
import { IconPlus, IconStack2 } from '@tabler/icons-react';
import { FC } from 'react';

interface ScenarioEmptyStateProps {
  onAdd: () => void;
}

/**
 * Shown when a scenario has no instances yet. Offers a single clear action
 * to add the first one instead of empty panels.
 */
export const ScenarioEmptyState: FC<ScenarioEmptyStateProps> = ({ onAdd }) => (
  <Paper withBorder radius="md" p="xl">
    <Stack align="center" gap="sm" py="xl">
      <ThemeIcon variant="default" size={48} radius="md">
        <IconStack2 size={24} stroke={1.5} />
      </ThemeIcon>
      <Text fw={600}>No instances in this scenario</Text>
      <Text size="sm" c="dimmed" ta="center" maw={440}>
        Add instances to run them together and correlate their data through
        shared global state.
      </Text>
      <Button mt="xs" leftSection={<IconPlus size={16} />} onClick={onAdd}>
        Add instance
      </Button>
    </Stack>
  </Paper>
);
