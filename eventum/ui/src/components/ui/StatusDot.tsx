import { FC } from 'react';

import { statusDotColorOrIdle } from './statusPalette';
import { GeneratorStatus } from '@/api/routes/generators/schemas';
import { describeInstanceStatus } from '@/pages/InstancesPage/InstancesTable/common/instance-status';

export interface StatusDotProps {
  /** Status to derive the dot's color from. A missing status (e.g. data
   *  not loaded yet) renders the idle color. */
  status: GeneratorStatus | undefined;
  /** Animate the dot while the status is mid-transition (Starting /
   *  Stopping). Off by default - opt in per call site. */
  pulse?: boolean;
}

/**
 * Small colored circle representing one instance's status, sourced from
 * the canonical statusPalette. Shared by StatusPill and InstanceBadges.
 */
export const StatusDot: FC<StatusDotProps> = ({ status, pulse = false }) => {
  const processing =
    pulse && !!status && describeInstanceStatus(status).processing;

  return (
    <span
      style={{
        display: 'block',
        width: 7,
        height: 7,
        borderRadius: '50%',
        background: statusDotColorOrIdle(status),
        animation: processing ? 'ev-pulse 2s infinite' : undefined,
      }}
    />
  );
};
