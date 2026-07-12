import { Box, Group, Text } from '@mantine/core';
import { FC } from 'react';

import { GeneratorsInfo } from '@/api/routes/generators/schemas';
import { describeInstanceStatus } from '@/pages/InstancesPage/InstancesTable/common/instance-status';

// Status buckets in display order, mapped to the semantic token palette.
// Core buckets always render (even at zero) so the fleet's health reads at a
// glance; transient buckets appear only while non-empty. `on`/`off` colours
// mirror the Home status breakdown: a semantic colour only while the bucket
// is non-empty, otherwise a muted/faint dot.
const CATEGORIES = [
  { label: 'Active', on: 'var(--ev-good)', off: 'var(--ev-faint)', core: true },
  {
    label: 'Starting',
    on: 'var(--ev-warn)',
    off: 'var(--ev-warn)',
    core: false,
  },
  {
    label: 'Stopping',
    on: 'var(--ev-warn)',
    off: 'var(--ev-warn)',
    core: false,
  },
  {
    label: 'Finished',
    on: 'var(--ev-cyan)',
    off: 'var(--ev-cyan)',
    core: false,
  },
  {
    label: 'Inactive',
    on: 'var(--ev-muted)',
    off: 'var(--ev-muted)',
    core: true,
  },
  { label: 'Failed', on: 'var(--ev-bad)', off: 'var(--ev-faint)', core: true },
];

interface FleetStatusProps {
  generators: GeneratorsInfo;
}

/** Compact fleet status for the page header: one chip per relevant status. */
export const FleetStatus: FC<FleetStatusProps> = ({ generators }) => {
  const counts: Record<string, number> = {};
  for (const g of generators) {
    const { text } = describeInstanceStatus(g.status);
    counts[text] = (counts[text] ?? 0) + 1;
  }

  const present = CATEGORIES.map((c) => {
    const count = counts[c.label] ?? 0;
    return { ...c, count, color: count > 0 ? c.on : c.off };
  }).filter((c) => c.core || c.count > 0);

  return (
    <Group gap="lg" wrap="nowrap">
      {present.map((c) => (
        <Group key={c.label} gap={7} wrap="nowrap">
          <Box
            style={{
              width: 8,
              height: 8,
              borderRadius: '50%',
              background: c.color,
            }}
          />
          <Text size="sm" c="dimmed">
            <Text span fw={700} style={{ color: 'var(--ev-text)' }}>
              {c.count}
            </Text>{' '}
            {c.label.toLowerCase()}
          </Text>
        </Group>
      ))}
    </Group>
  );
};
