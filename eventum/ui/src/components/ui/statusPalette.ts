import { GeneratorStatus } from '@/api/routes/generators/schemas';
import { describeInstanceStatus } from '@/pages/InstancesPage/InstancesTable/common/instance-status';

export type Variant = 'good' | 'warn' | 'bad' | 'done' | 'idle';

// Map the status text from instance-status.ts to one token-driven variant.
// This table is the only place a status's color is decided; instance-
// status.ts only classifies the text/processing flag, not the color.
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

/** Neutral dot color for aggregate buckets that mix several variants
 *  (e.g. an "inactive" total spanning finished + failed + idle) and
 *  therefore don't map to a single Variant. */
export const AGGREGATE_DOT_COLOR = 'var(--ev-muted)';

export function statusVariant(status: GeneratorStatus): Variant {
  const { text } = describeInstanceStatus(status);
  return TEXT_TO_VARIANT[text] ?? 'idle';
}

/** Dot color for an instance status, from the unified status palette.
 *  Shared by the status pill and the instance badges. */
export function statusDotColor(status: GeneratorStatus): string {
  return VARIANT_STYLE[statusVariant(status)].dot;
}

/** Dot color for an instance status that may not be known yet (e.g. data
 *  still loading). A missing status renders the idle color. */
export function statusDotColorOrIdle(
  status: GeneratorStatus | undefined
): string {
  return status ? statusDotColor(status) : VARIANT_STYLE.idle.dot;
}

export type StatusLeaf = 'active' | 'finished' | 'failed' | 'idle';

/** Coarse lifecycle leaf. Transitional states (starting/stopping) count as
 *  active; ended states split into finished (success) and failed; a generator
 *  that has never ended and is not running is idle. finished + failed + idle
 *  together form the "inactive" (not-running) total. */
export function instanceStatusLeaf(status: GeneratorStatus): StatusLeaf {
  if (status.is_running || status.is_initializing || status.is_stopping) {
    return 'active';
  }
  if (status.is_ended_up) {
    return status.is_ended_up_successfully ? 'finished' : 'failed';
  }
  return 'idle';
}

export type ScenarioStatusBucket =
  | 'running'
  | 'initializing'
  | 'stopping'
  | 'stopped';

/** Classify a status into the 4 buckets the Scenarios table needs, keeping
 *  "initializing"/"stopping" visible on their own instead of folding them
 *  into instanceStatusLeaf's coarser "active". A missing status (generator
 *  not found) counts as stopped. */
export function scenarioStatusBucket(
  status: GeneratorStatus | undefined
): ScenarioStatusBucket {
  if (!status) return 'stopped';
  if (status.is_initializing) return 'initializing';
  if (status.is_stopping) return 'stopping';
  if (status.is_running) return 'running';
  return 'stopped';
}

export interface InstanceStatusCounts {
  total: number;
  active: number;
  /** Not-running total: finished + failed + idle. */
  inactive: number;
  finished: number;
  failed: number;
  idle: number;
}

/** Count instances into the status summary shared by the Home rail and the
 *  Monitoring header: active vs inactive, with the inactive breakdown. */
export function summarizeInstanceStatuses(
  statuses: GeneratorStatus[]
): InstanceStatusCounts {
  const counts = { active: 0, finished: 0, failed: 0, idle: 0 };

  for (const status of statuses) {
    counts[instanceStatusLeaf(status)] += 1;
  }

  return {
    total: statuses.length,
    active: counts.active,
    inactive: counts.finished + counts.failed + counts.idle,
    finished: counts.finished,
    failed: counts.failed,
    idle: counts.idle,
  };
}
