import { Button, Code, Paper, Stack, Text, ThemeIcon } from '@mantine/core';
import { IconLock, IconPlus } from '@tabler/icons-react';
import { FC } from 'react';

interface SecretsEmptyStateProps {
  onAdd: () => void;
}

/**
 * Shown when the keyring holds no secrets yet. Explains what a secret is
 * for and how it is referenced, then offers the single action to add one.
 */
export const SecretsEmptyState: FC<SecretsEmptyStateProps> = ({ onAdd }) => (
  <Paper withBorder p="xl">
    <Stack align="center" gap="sm" py="xl">
      <ThemeIcon variant="default" size={48} radius="md">
        <IconLock size={24} stroke={1.5} />
      </ThemeIcon>
      <Text fw={600}>No secrets yet</Text>
      <Text size="sm" c="dimmed" ta="center" maw={460}>
        Store an API key, token, or password in the keyring, then reference it
        in configuration as <Code>{'${secrets.name}'}</Code>.
      </Text>
      <Button mt="xs" leftSection={<IconPlus size={16} />} onClick={onAdd}>
        Add secret
      </Button>
    </Stack>
  </Paper>
);
