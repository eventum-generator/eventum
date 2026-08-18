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
 * What a running instance occupies, under the throughput it occupies it for:
 * the rates it moves events at and the totals of the run, then the processor
 * it takes, the memory its queues hold and the bytes it moves. Both halves
 * answer "what is this instance costing", so they belong together and above
 * the two views that explain them.
 */
export const LivePanel: FC<LivePanelProps> = ({
  stats,
  inputEps,
  outputEps,
  cpuPercent,
}) => (
  <Section label="Resources">
    <Stack gap="md">
      <InstanceState stats={stats} inputEps={inputEps} outputEps={outputEps} />
      <Divider />
      <ResourceGroups resources={stats.resources} cpuPercent={cpuPercent} />
    </Stack>
  </Section>
);
