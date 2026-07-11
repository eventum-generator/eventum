import { FC } from 'react';

import { GeneratorStatus } from '@/api/routes/generators/schemas';
import { describeInstanceStatus } from '@/pages/InstancesPage/InstancesTable/common/instance-status';

type Variant = 'good' | 'warn' | 'bad' | 'idle';

// Map the existing status text to one token-driven variant, replacing the
// raw-hex colors in instance-status.ts with the unified semantic palette.
const TEXT_TO_VARIANT: Record<string, Variant> = {
  Active: 'good',
  Starting: 'warn',
  Stopping: 'warn',
  Failed: 'bad',
  Finished: 'good',
  Inactive: 'idle',
};

const VARIANT_STYLE: Record<Variant, { bg: string; fg: string; dot: string }> =
  {
    good: {
      bg: 'var(--ev-good-soft)',
      fg: 'var(--ev-good)',
      dot: 'var(--ev-good)',
    },
    warn: {
      bg: 'var(--ev-warn-soft)',
      fg: 'var(--ev-warn)',
      dot: 'var(--ev-warn)',
    },
    bad: {
      bg: 'var(--ev-bad-soft)',
      fg: 'var(--ev-bad)',
      dot: 'var(--ev-bad)',
    },
    idle: {
      bg: 'var(--ev-surface-2)',
      fg: 'var(--ev-muted)',
      dot: 'var(--ev-faint)',
    },
  };

export const StatusPill: FC<{ status: GeneratorStatus }> = ({ status }) => {
  const { text, processing } = describeInstanceStatus(status);
  const variant = TEXT_TO_VARIANT[text] ?? 'idle';
  const s = VARIANT_STYLE[variant];

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
      <span
        style={{
          width: 7,
          height: 7,
          borderRadius: '50%',
          background: s.dot,
          animation: processing ? 'ev-pulse 2s infinite' : undefined,
        }}
      />
      {text}
    </span>
  );
};
