import { Divider, Stack } from '@mantine/core';
import { FC } from 'react';

import { Section } from '../primitives';
import { InstanceState } from './InstanceState';
import { ResourceGroups } from './ResourceGroups';
import { GeneratorStats } from '@/api/routes/generators/schemas';

interface LivePanelProps {
  stats: GeneratorStats;
  inputEps: number;
  outputEps: number;
  cpuPercent: number;
}

/**
 * The state of a running instance in one panel: what it moves right now, and
 * underneath, what that costs - the processor it takes, the memory its queues
 * hold and the bytes it moves. Both halves answer "how is it doing", so they
 * belong together and above the two views that explain them.
 */
export const LivePanel: FC<LivePanelProps> = ({
  stats,
  inputEps,
  outputEps,
  cpuPercent,
}) => (
  <Section label="Now">
    <Stack gap="md">
      <InstanceState stats={stats} inputEps={inputEps} outputEps={outputEps} />
      <Divider />
      <ResourceGroups resources={stats.resources} cpuPercent={cpuPercent} />
    </Stack>
  </Section>
);
