import { describe, expect, it } from 'vitest';

import { describeInstanceStatus } from './instance-status';
import { GeneratorStatus } from '@/api/routes/generators/schemas';

const status = (overrides: Partial<GeneratorStatus>): GeneratorStatus => ({
  is_initializing: false,
  is_running: false,
  is_stopping: false,
  is_ended_up: false,
  is_ended_up_successfully: false,
  ...overrides,
});

describe('describeInstanceStatus', () => {
  // "Inactive" is the total covering every instance at rest, so the state of
  // an instance that has not run is named Idle - the same word the fleet
  // summary breaks that total down with.
  it.each([
    [{ is_running: true }, 'Active', false],
    [{ is_initializing: true }, 'Starting', true],
    [{ is_stopping: true }, 'Stopping', true],
    [{ is_ended_up: true, is_ended_up_successfully: true }, 'Finished', false],
    [{ is_ended_up: true }, 'Failed', false],
    [{}, 'Idle', false],
  ])('reads %o as %s', (flags, text, processing) => {
    expect(describeInstanceStatus(status(flags))).toEqual({ text, processing });
  });

  it('reads a stopping instance as stopping even once it has ended', () => {
    expect(
      describeInstanceStatus(status({ is_stopping: true, is_ended_up: true }))
        .text
    ).toBe('Stopping');
  });
});
