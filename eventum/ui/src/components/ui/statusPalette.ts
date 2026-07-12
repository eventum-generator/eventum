import { GeneratorStatus } from '@/api/routes/generators/schemas';
import { describeInstanceStatus } from '@/pages/InstancesPage/InstancesTable/common/instance-status';

export type Variant = 'good' | 'warn' | 'bad' | 'done' | 'idle';

// Map the existing status text to one token-driven variant, replacing the
// raw-hex colors in instance-status.ts with the unified semantic palette.
// "done" is a terminal-success state at rest - it must read as calmer than
// the live "good" (Active) so a finished instance is not mistaken for a
// running one.
const TEXT_TO_VARIANT: Record<string, Variant> = {
  Active: 'good',
  Starting: 'warn',
  Stopping: 'warn',
  Failed: 'bad',
  Finished: 'done',
  Inactive: 'idle',
};

export const VARIANT_STYLE: Record<
  Variant,
  { bg: string; fg: string; dot: string }
> = {
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
  done: {
    bg: 'var(--ev-done-bg)',
    fg: 'var(--ev-done-fg)',
    dot: 'var(--ev-done-dot)',
  },
  idle: {
    bg: 'var(--ev-surface-2)',
    fg: 'var(--ev-muted)',
    dot: 'var(--ev-faint)',
  },
};

export function statusVariant(status: GeneratorStatus): Variant {
  const { text } = describeInstanceStatus(status);
  return TEXT_TO_VARIANT[text] ?? 'idle';
}

/** Dot color for an instance status, from the unified status palette.
 *  Shared by the status pill and the instance badges. */
export function statusDotColor(status: GeneratorStatus): string {
  return VARIANT_STYLE[statusVariant(status)].dot;
}
