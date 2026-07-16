import { FC } from 'react';

import { StatusDot } from './StatusDot';
import { VARIANT_STYLE, statusVariant } from './statusPalette';
import { GeneratorStatus } from '@/api/routes/generators/schemas';
import { describeInstanceStatus } from '@/pages/InstancesPage/InstancesTable/common/instance-status';

export const StatusPill: FC<{ status: GeneratorStatus }> = ({ status }) => {
  const { text } = describeInstanceStatus(status);
  const s = VARIANT_STYLE[statusVariant(status)];

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 7,
        height: 24,
        padding: '0 10px',
        borderRadius: 999,
        fontSize: 12,
        fontWeight: 600,
        background: s.bg,
        color: s.fg,
      }}
    >
      <StatusDot status={status} pulse />
      {text}
    </span>
  );
};
