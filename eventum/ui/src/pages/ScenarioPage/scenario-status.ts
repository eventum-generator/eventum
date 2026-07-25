import { GeneratorStatus } from '@/api/routes/generators/schemas';
import { scenarioStatusBucket } from '@/components/ui/statusPalette';

export interface ScenarioStatusCounts {
  total: number;
  running: number;
  initializing: number;
  stopping: number;
  /** Not-running total (never started, finished, or failed). */
  inactive: number;
}

/** Count a scenario's member statuses into the buckets the header needs. A
 *  missing status (generator not found) counts as inactive. */
export function summarizeScenarioStatuses(
  statuses: (GeneratorStatus | undefined)[]
): ScenarioStatusCounts {
  const counts: ScenarioStatusCounts = {
    total: statuses.length,
    running: 0,
    initializing: 0,
    stopping: 0,
    inactive: 0,
  };

  for (const status of statuses) {
    const bucket = scenarioStatusBucket(status);
    if (bucket === 'running') counts.running += 1;
    else if (bucket === 'initializing') counts.initializing += 1;
    else if (bucket === 'stopping') counts.stopping += 1;
    else counts.inactive += 1;
  }

  return counts;
}

/** Instances "Start all" can act on: everything not already running or
 *  starting. Mirrors the page's start guard (`!is_running &&
 *  !is_initializing`) so the button disables exactly when it is a no-op. */
export function startableCount(counts: ScenarioStatusCounts): number {
  return counts.inactive + counts.stopping;
}

/** Instances "Stop all" can act on: anything not already fully stopped. */
export function stoppableCount(counts: ScenarioStatusCounts): number {
  return counts.running + counts.initializing + counts.stopping;
}
