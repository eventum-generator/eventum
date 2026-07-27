import { GeneratorStatus } from '@/api/routes/generators/schemas';
import { describeInstanceStatus } from '@/pages/InstancesPage/InstancesTable/common/instance-status';

export type Variant = 'good' | 'warn' | 'bad' | 'done' | 'idle';

// Map the status text from instance-status.ts to one token-driven variant.
// This table is the only place a status's color is decided; instance-
// status.ts only classifies the text/processing flag, not the color.
// "done" is a terminal-success state at rest - whether an instance is still
// running has to be answerable from its chip alone, with no running chip
// nearby to compare against.
const TEXT_TO_VARIANT: Record<string, Variant> = {
  Active: 'good',
  Starting: 'warn',
  Stopping: 'warn',
  Failed: 'bad',
  Finished: 'done',
  Inactive: 'idle',
};

/** Chip palette and indicator shade per variant. `color` tints the chip and
 *  colors its label - a chip reads `-light` for its fill and `-light-color`
 *  for its label, which keeps the text legible in both schemes. `dot` names
 *  the shade the indicator takes: shade 4 is the vivid end of a ramp, so a
 *  live state reads as switched on.
 *
 *  A chip stays colored only while the instance is live. The states at rest
 *  share the neutral chip and name their outcome through the indicator alone,
 *  at a shade deep enough to read as switched off - a colored chip of any
 *  shade reads as a live one once diluted to a tint, and in a table the two
 *  sit rows apart with nothing to compare against. */
const VARIANT_COLOR: Record<Variant, { color: string; dot: string }> = {
  good: { color: 'green', dot: 'var(--mantine-color-green-4)' },
  warn: { color: 'yellow', dot: 'var(--mantine-color-yellow-4)' },
  bad: { color: 'gray', dot: 'var(--mantine-color-red-7)' },
  done: { color: 'gray', dot: 'var(--mantine-color-green-6)' },
  idle: { color: 'gray', dot: 'var(--mantine-color-gray-light-color)' },
};

export const VARIANT_STYLE: Record<
  Variant,
  { bg: string; fg: string; dot: string }
> = Object.fromEntries(
  Object.entries(VARIANT_COLOR).map(([variant, { color, dot }]) => [
    variant,
    {
      bg: `var(--mantine-color-${color}-light)`,
      fg: `var(--mantine-color-${color}-light-color)`,
      dot,
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
