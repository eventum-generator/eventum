import { GeneratorStatus } from '@/api/routes/generators/schemas';

/** What a stuck instance means, since the word alone does not say why it
 *  will neither start nor stop. */
export const STUCK_HINT =
  'Did not stop or did not finish starting: a plugin keeps running until the Eventum process restarts';

/** Classify a status into its display text and whether it is mid-
 *  transition. Color is not part of this result - derive it from
 *  `statusPalette.ts`, the canonical status-to-color source.
 *
 *  Stuck wins over every other flag: the instance did not stop or did not
 *  finish starting,
 *  so it still reads as running (or starting) while nothing will move it
 *  on - and it is not mid-transition either. */
export function describeInstanceStatus(status: GeneratorStatus): {
  text: string;
  processing: boolean;
} {
  let text = 'Idle';
  let processing = false;

  if (status.is_abandoned) {
    text = 'Stuck';
  } else if (status.is_initializing) {
    text = 'Starting';
    processing = true;
  } else if (status.is_stopping) {
    text = 'Stopping';
    processing = true;
  } else if (status.is_running) {
    text = 'Active';
  } else if (status.is_ended_up) {
    text = status.is_ended_up_successfully ? 'Finished' : 'Failed';
  }

  return { text, processing };
}
