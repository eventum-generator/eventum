import { FC } from 'react';

import { ScenarioStatusCounts } from './scenario-status';
import { StatusChip } from '@/components/ui/StatusChip';
import { Variant } from '@/components/ui/statusPalette';

/**
 * Aggregate status of a whole scenario, shown next to its name. Running wins
 * over the transitional states so a scenario with any live instance reads as
 * up; an all-idle scenario reads as inactive.
 */
export const ScenarioStatusPill: FC<{ counts: ScenarioStatusCounts }> = ({
  counts,
}) => {
  let variant: Variant = 'idle';
  let label = 'Inactive';

  if (counts.running > 0) {
    variant = 'good';
    label = 'Running';
  } else if (counts.initializing > 0) {
    variant = 'warn';
    label = 'Starting';
  } else if (counts.stopping > 0) {
    variant = 'warn';
    label = 'Stopping';
  }

  return <StatusChip variant={variant}>{label}</StatusChip>;
};
