import { Tooltip } from '@mantine/core';
import { FC } from 'react';

import { StatusChip } from './StatusChip';
import { StatusDot } from './StatusDot';
import { statusVariant } from './statusPalette';
import { GeneratorStatus } from '@/api/routes/generators/schemas';
import {
  STUCK_HINT,
  describeInstanceStatus,
} from '@/pages/InstancesPage/InstancesTable/common/instance-status';

export const StatusPill: FC<{ status: GeneratorStatus }> = ({ status }) => {
  const { text } = describeInstanceStatus(status);
  const variant = statusVariant(status);

  const chip = (
    <StatusChip variant={variant} dot={<StatusDot status={status} pulse />}>
      {text}
    </StatusChip>
  );

  if (variant !== 'stuck') {
    return chip;
  }

  return (
    <Tooltip label={STUCK_HINT} multiline maw={260} withArrow>
      <span style={{ display: 'inline-flex' }}>{chip}</span>
    </Tooltip>
  );
};
