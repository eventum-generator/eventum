import { GeneratorStatus } from '@/api/routes/generators/schemas';

/** Classify a status into its display text and whether it is mid-
 *  transition. Color is not part of this result - derive it from
 *  `statusPalette.ts`, the canonical status-to-color source. */
export function describeInstanceStatus(status: GeneratorStatus): {
  text: string;
  processing: boolean;
} {
  let text = 'Inactive';
  let processing = false;

  if (status.is_initializing) {
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
