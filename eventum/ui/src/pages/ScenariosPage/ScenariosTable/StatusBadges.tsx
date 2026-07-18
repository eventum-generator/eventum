import { Group } from '@mantine/core';
import { FC, ReactNode } from 'react';

import { ScenarioRow } from './types';
import { StatusChip } from '@/components/ui/StatusChip';

interface StatusBadgesProps {
  readonly row: ScenarioRow;
}

/**
 * Aggregate status of a scenario's instances, rendered as one count chip
 * per non-empty bucket. A scenario groups many instances, so unlike an
 * instance's single StatusPill it may show several chips at once (e.g.
 * "3 active" + "1 starting"); an all-inactive scenario collapses to a
 * single idle chip.
 */
export const StatusBadges: FC<StatusBadgesProps> = ({ row }) => {
  const chips: ReactNode[] = [];

  if (row.runningCount > 0) {
    chips.push(
      <StatusChip key="running" variant="good">
        {row.runningCount} active
      </StatusChip>
    );
  }

  if (row.initializingCount > 0) {
    chips.push(
      <StatusChip key="starting" variant="warn">
        {row.initializingCount} starting
      </StatusChip>
    );
  }

  if (row.stoppingCount > 0) {
    chips.push(
      <StatusChip key="stopping" variant="warn">
        {row.stoppingCount} stopping
      </StatusChip>
    );
  }

  // Show the inactive remainder only when it sits next to active buckets;
  // an entirely inactive scenario is covered by the fallback chip below.
  if (row.stoppedCount > 0 && chips.length > 0) {
    chips.push(
      <StatusChip key="inactive" variant="idle">
        {row.stoppedCount} inactive
      </StatusChip>
    );
  }

  if (chips.length === 0) {
    return <StatusChip variant="idle">Inactive</StatusChip>;
  }

  return <Group gap="xs">{chips}</Group>;
};
