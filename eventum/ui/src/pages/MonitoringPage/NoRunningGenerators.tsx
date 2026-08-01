import { Anchor, Paper, Stack, Text, ThemeIcon } from '@mantine/core';
import { IconActivity } from '@tabler/icons-react';
import { FC } from 'react';
import { Link } from 'react-router-dom';

import { ROUTE_PATHS } from '@/routing/paths';

/**
 * Shown in place of the live pipeline and throughput sections when no
 * generator is currently running - those views have no data to display
 * until generation starts. Resource tiles stay visible since host and
 * process metrics are always live.
 */
export const NoRunningGenerators: FC = () => (
  <Paper withBorder p="xl">
    <Stack align="center" gap="sm" py="xl">
      <ThemeIcon variant="default" size={48} radius="md">
        <IconActivity size={24} stroke={1.5} />
      </ThemeIcon>
      <Text fw={600}>No running generators</Text>
      <Text size="sm" c="dimmed" ta="center" maw={400}>
        Start a generator to see live pipeline flow and throughput here.
      </Text>
      <Anchor component={Link} to={ROUTE_PATHS.INSTANCES} size="sm">
        Go to Instances
      </Anchor>
    </Stack>
  </Paper>
);
