import { describe, expect, it } from 'vitest';

import {
  startableCount,
  stoppableCount,
  summarizeScenarioStatuses,
} from './scenario-status';
import { GeneratorStatus } from '@/api/routes/generators/schemas';

const IDLE: GeneratorStatus = {
  is_initializing: false,
  is_running: false,
  is_ended_up: false,
  is_ended_up_successfully: false,
  is_stopping: false,
  is_abandoned: false,
};

const RUNNING: GeneratorStatus = { ...IDLE, is_running: true };
const STUCK: GeneratorStatus = {
  ...IDLE,
  is_running: true,
  is_abandoned: true,
};

describe('summarizeScenarioStatuses', () => {
  it('counts a stuck instance apart from the running ones', () => {
    const counts = summarizeScenarioStatuses([STUCK, RUNNING, IDLE]);

    expect(counts).toEqual({
      total: 3,
      stuck: 1,
      running: 1,
      initializing: 0,
      stopping: 0,
      inactive: 1,
    });
  });

  it('counts an instance it cannot find as inactive', () => {
    expect(summarizeScenarioStatuses([undefined]).inactive).toBe(1);
  });
});

/**
 * A stuck instance refuses a start and answers a stop with an error, so
 * neither bulk action counts it as something it can act on.
 */
describe('the bulk actions', () => {
  it('leave a stuck instance out of what they can start or stop', () => {
    const counts = summarizeScenarioStatuses([STUCK]);

    expect(startableCount(counts)).toBe(0);
    expect(stoppableCount(counts)).toBe(0);
  });
});
