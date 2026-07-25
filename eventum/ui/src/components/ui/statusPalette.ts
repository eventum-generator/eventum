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

/** Mantine palette backing each variant, and whether the variant has a lit
 *  state. A chip reads `-light` for its fill and `-light-color` for its label,
 *  which keeps the text legible in both schemes; the dot of a lit variant
 *  jumps to shade 4 - the vivid end of the ramp - so a running instance reads
 *  as switched on rather than merely coloured. */
const VARIANT_COLOR: Record<Variant, { color: string; lit: boolean }> = {
  good: { color: 'green', lit: true },
  warn: { color: 'yellow', lit: true },
  bad: { color: 'red', lit: true },
  // Terminal success at rest: teal is settled where green is lit, so a
  // finished instance is not mistaken for a running one.
  done: { color: 'teal', lit: false },
  idle: { color: 'gray', lit: false },
};

export const VARIANT_STYLE: Record<
  Variant,
  { bg: string; fg: string; dot: string }
> = Object.fromEntries(
  Object.entries(VARIANT_COLOR).map(([variant, { color, lit }]) => [
    variant,
    {
      bg: `var(--mantine-color-${color}-light)`,
      fg: `var(--mantine-color-${color}-light-color)`,
      dot: lit
        ? `var(--mantine-color-${color}-4)`
        : `var(--mantine-color-${color}-light-color)`,
    },
  ])
) as Record<Variant, { bg: string; fg: string; dot: string }>;

/** Neutral dot color for aggregate buckets that mix several variants
 *  (e.g. an "inactive" total spanning finished + failed + idle) and
 *  therefore don't map to a single Variant. */
export const AGGREGATE_DOT_COLOR = 'var(--mantine-color-dimmed)';

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
