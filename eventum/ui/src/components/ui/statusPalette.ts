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

export type StatusBucket = 'active' | 'finished' | 'inactive' | 'failed';

/** Coarse lifecycle bucket for the status summaries. Transitional states
 *  (starting/stopping) count as active; ended states split into finished
 *  (success) and failed; everything else is inactive. */
export function instanceStatusBucket(status: GeneratorStatus): StatusBucket {
  if (status.is_running || status.is_initializing || status.is_stopping) {
    return 'active';
  }
  if (status.is_ended_up) {
    return status.is_ended_up_successfully ? 'finished' : 'failed';
  }
  return 'inactive';
}

export interface StatusBucketSummary {
  key: StatusBucket;
  label: string;
  count: number;
  /** Dot color: the bucket's semantic color when non-empty, faint at zero. */
  color: string;
}

const BUCKET_ORDER: { key: StatusBucket; label: string; color: string }[] = [
  { key: 'active', label: 'active', color: 'var(--ev-good)' },
  { key: 'finished', label: 'finished', color: 'var(--ev-done-dot)' },
  { key: 'inactive', label: 'inactive', color: 'var(--ev-muted)' },
  { key: 'failed', label: 'failed', color: 'var(--ev-bad)' },
];

/** Count instances into the four display buckets, in display order, each with
 *  its dot color (faint when empty). Single source for the Home and Monitoring
 *  status summaries. */
export function summarizeInstanceStatuses(
  statuses: GeneratorStatus[]
): StatusBucketSummary[] {
  const counts: Record<StatusBucket, number> = {
    active: 0,
    finished: 0,
    inactive: 0,
    failed: 0,
  };

  for (const status of statuses) {
    counts[instanceStatusBucket(status)] += 1;
  }

  return BUCKET_ORDER.map((bucket) => ({
    key: bucket.key,
    label: bucket.label,
    count: counts[bucket.key],
    color: counts[bucket.key] > 0 ? bucket.color : 'var(--ev-faint)',
  }));
}
