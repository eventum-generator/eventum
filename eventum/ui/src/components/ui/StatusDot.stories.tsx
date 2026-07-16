import { Group, Stack, Text } from '@mantine/core';
import type { Meta, StoryObj } from '@storybook/react-vite';

import { StatusDot } from './StatusDot';
import { GeneratorStatus } from '@/api/routes/generators/schemas';

/** One fixture per status text that `describeInstanceStatus` can produce,
 *  plus the "no status yet" case StatusDot also handles. Exercises the
 *  full statusPalette by proxy. */
const STATUSES: Record<string, GeneratorStatus | undefined> = {
  Starting: {
    is_initializing: true,
    is_running: false,
    is_ended_up: false,
    is_ended_up_successfully: false,
    is_stopping: false,
  },
  Active: {
    is_initializing: false,
    is_running: true,
    is_ended_up: false,
    is_ended_up_successfully: false,
    is_stopping: false,
  },
  Stopping: {
    is_initializing: false,
    is_running: true,
    is_ended_up: false,
    is_ended_up_successfully: false,
    is_stopping: true,
  },
  Finished: {
    is_initializing: false,
    is_running: false,
    is_ended_up: true,
    is_ended_up_successfully: true,
    is_stopping: false,
  },
  Failed: {
    is_initializing: false,
    is_running: false,
    is_ended_up: true,
    is_ended_up_successfully: false,
    is_stopping: false,
  },
  Inactive: {
    is_initializing: false,
    is_running: false,
    is_ended_up: false,
    is_ended_up_successfully: false,
    is_stopping: false,
  },
  'Not loaded yet': undefined,
};

const meta: Meta<typeof StatusDot> = {
  title: 'Atoms/StatusDot',
  component: StatusDot,
};
export default meta;

/** Smoke story: proves the Storybook pipeline renders through the real
 *  theme (tokens, Mantine components) in both color schemes, across
 *  every status the dot can represent. */
export const Statuses: StoryObj<typeof StatusDot> = {
  render: () => (
    <Stack gap="sm">
      {Object.entries(STATUSES).map(([label, status]) => (
        <Group key={label} gap="sm">
          <StatusDot status={status} pulse />
          <Text size="sm">{label}</Text>
        </Group>
      ))}
    </Stack>
  ),
};
