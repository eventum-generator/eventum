import { FC } from 'react';

import { StatusChip } from './StatusChip';
import { StatusDot } from './StatusDot';
import { statusVariant } from './statusPalette';
import { GeneratorStatus } from '@/api/routes/generators/schemas';
import { describeInstanceStatus } from '@/pages/InstancesPage/InstancesTable/common/instance-status';

export const StatusPill: FC<{ status: GeneratorStatus }> = ({ status }) => {
  const { text } = describeInstanceStatus(status);

  return (
    <StatusChip
      variant={statusVariant(status)}
      dot={<StatusDot status={status} pulse />}
    >
      {text}
    </StatusChip>
  );
};
