import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { InstanceStatusSummary } from './InstanceStatusSummary';
import { GeneratorStatus } from '@/api/routes/generators/schemas';
import { renderWithProviders } from '@/test/render';

const IDLE: GeneratorStatus = {
  is_initializing: false,
  is_running: false,
  is_ended_up: false,
  is_ended_up_successfully: false,
  is_stopping: false,
};

const RUNNING: GeneratorStatus = { ...IDLE, is_running: true };
const STARTING: GeneratorStatus = { ...IDLE, is_initializing: true };
const STOPPING: GeneratorStatus = { ...IDLE, is_stopping: true };
const FINISHED: GeneratorStatus = {
  ...IDLE,
  is_ended_up: true,
  is_ended_up_successfully: true,
};
const FAILED: GeneratorStatus = { ...IDLE, is_ended_up: true };

function setup(statuses: GeneratorStatus[]) {
  renderWithProviders(<InstanceStatusSummary statuses={statuses} />);
}

/** The figure a bucket carries, by its label. */
function count(label: string): string {
  const text = screen.getByText(label).closest('p');

  return (text?.textContent ?? '').replace(label, '').trim();
}

/**
 * The summary is what the fleet is doing, in one line: how much of it is
 * live and, of the rest, how it ended. An instance is in exactly one
 * bucket, and an instance still on the move counts as live - it is doing
 * something, and reading it as inactive would say the fleet is idle
 * while it starts.
 */
describe('InstanceStatusSummary', () => {
  it('counts a running instance as active', () => {
    setup([RUNNING, IDLE]);

    expect(count('active')).toBe('1');
    expect(count('inactive')).toBe('1');
  });

  it.each([
    ['starting', STARTING],
    ['stopping', STOPPING],
  ])('counts an instance %s as active', (_label, status) => {
    setup([status]);

    expect(count('active')).toBe('1');
    expect(count('inactive')).toBe('0');
  });

  it('tells the outcomes of the instances at rest apart', () => {
    setup([FINISHED, FAILED, IDLE]);

    expect(count('inactive')).toBe('3');
    expect(count('finished')).toBe('1');
    expect(count('failed')).toBe('1');
    expect(count('idle')).toBe('1');
  });

  it('counts a run that ended badly as failed rather than finished', () => {
    setup([FAILED]);

    expect(count('failed')).toBe('1');
    expect(count('finished')).toBe('0');
  });

  it('counts nothing when there is no instance', () => {
    setup([]);

    expect(count('active')).toBe('0');
    expect(count('inactive')).toBe('0');
  });

  it('lights the dot of a bucket that counts something', () => {
    setup([RUNNING]);

    // Only a bucket with instances in it is lit, so an empty fleet does
    // not read as a live one.
    const lit = [...document.querySelectorAll('.ev-status-dot')].filter(
      (dot) => (dot as HTMLElement).dataset.glow === 'true'
    );

    expect(lit).toHaveLength(1);
  });

  it('leaves every dot at rest when nothing runs', () => {
    setup([IDLE, FINISHED]);

    expect(
      [...document.querySelectorAll('.ev-status-dot')].filter(
        (dot) => (dot as HTMLElement).dataset.glow === 'true'
      )
    ).toHaveLength(0);
  });
});
