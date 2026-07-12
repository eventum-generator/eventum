import { Box, Group, Text } from '@mantine/core';
import { FC } from 'react';

import { GeneratorsInfo } from '@/api/routes/generators/schemas';
import { summarizeInstanceStatuses } from '@/components/ui/statusPalette';

interface FleetStatusProps {
  generators: GeneratorsInfo;
}

/** Compact fleet status for the page header: one chip per status bucket
 *  (active / finished / inactive / failed), sharing the Home summary. */
export const FleetStatus: FC<FleetStatusProps> = ({ generators }) => {
  const buckets = summarizeInstanceStatuses(generators.map((g) => g.status));

  return (
    <Group gap="lg" wrap="nowrap">
      {buckets.map((b) => (
        <Group key={b.key} gap={7} wrap="nowrap">
          <Box
            style={{
              width: 8,
              height: 8,
              borderRadius: '50%',
              background: b.color,
            }}
          />
          <Text size="sm" c="dimmed">
            <Text span fw={700} style={{ color: 'var(--ev-text)' }}>
              {b.count}
            </Text>{' '}
            {b.label}
          </Text>
        </Group>
      ))}
    </Group>
  );
};
