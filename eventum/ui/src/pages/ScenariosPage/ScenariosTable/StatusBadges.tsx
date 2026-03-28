import { Group, Indicator, Text } from '@mantine/core';
import { FC, ReactNode } from 'react';

import { ScenarioRow } from './types';

interface StatusBadgesProps {
  readonly row: ScenarioRow;
}

export const StatusBadges: FC<StatusBadgesProps> = ({ row }) => {
  const parts: ReactNode[] = [];

  if (row.runningCount > 0) {
    parts.push(
      <Group key="running" gap="sm" align="center" wrap="nowrap">
        <Indicator
          color="green.6"
          size={8}
          position="middle-center"
          />
        <Text size="sm">{row.runningCount} active</Text>
      </Group>
    );
  }

  if (row.stoppingCount > 0) {
    parts.push(
      <Group key="stopping" gap="sm" align="center" wrap="nowrap">
        <Indicator color="yellow.7" size={8} position="middle-center" />
        <Text size="sm">{row.stoppingCount} stopping</Text>
      </Group>
    );
  }

  if (row.initializingCount > 0) {
    parts.push(
      <Group key="initializing" gap="sm" align="center" wrap="nowrap">
        <Indicator color="yellow.7" size={8} position="middle-center" />
        <Text size="sm">{row.initializingCount} starting</Text>
      </Group>
    );
  }

  if (row.stoppedCount > 0 && (row.runningCount > 0 || row.initializingCount > 0 || row.stoppingCount > 0)) {
    parts.push(
      <Group key="stopped" gap="sm" align="center" wrap="nowrap">
        <Indicator color="gray.6" size={8} position="middle-center" />
        <Text size="sm">{row.stoppedCount} inactive</Text>
      </Group>
    );
  }

  if (parts.length === 0) {
    return (
      <Group gap="sm" align="center" wrap="nowrap">
        <Indicator color="gray.6" size={8} position="middle-center" />
        <Text size="sm">Inactive</Text>
      </Group>
    );
  }

  return <Group gap="md">{parts}</Group>;
};
