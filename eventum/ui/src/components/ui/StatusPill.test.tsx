import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { StatusChip } from './StatusChip';
import { StatusDot } from './StatusDot';
import { StatusPill } from './StatusPill';
import { GeneratorStatus } from '@/api/routes/generators/schemas';
import { renderWithProviders } from '@/test/render';

const IDLE: GeneratorStatus = {
  is_initializing: false,
  is_running: false,
  is_ended_up: false,
  is_ended_up_successfully: false,
  is_stopping: false,
};

const STATUSES: [string, GeneratorStatus][] = [
  ['Idle', IDLE],
  ['Starting', { ...IDLE, is_initializing: true }],
  ['Active', { ...IDLE, is_running: true }],
  ['Stopping', { ...IDLE, is_stopping: true }],
  ['Finished', { ...IDLE, is_ended_up: true, is_ended_up_successfully: true }],
  ['Failed', { ...IDLE, is_ended_up: true }],
];

function dot(): HTMLElement {
  const found = document.querySelector('.ev-status-dot');

  if (found === null) {
    throw new Error('the status chip drew no dot');
  }

  return found as HTMLElement;
}

/**
 * The pill is the one place a status is named and coloured, so what it
 * shows has to match what the status actually is - and the animation is
 * reserved for the two states that are mid-transition, where it is the
 * only signal that something is still happening.
 */
describe('StatusPill', () => {
  it.each(STATUSES)(
    'names a status the instance is in as %s',
    (text, status) => {
      renderWithProviders(<StatusPill status={status} />);

      expect(screen.getByText(text)).toBeInTheDocument();
    }
  );

  it.each([
    ['Starting', { ...IDLE, is_initializing: true }],
    ['Stopping', { ...IDLE, is_stopping: true }],
  ])('animates the dot while %s', (_text, status) => {
    renderWithProviders(<StatusPill status={status} />);

    expect(dot()).toHaveAttribute('data-processing', 'true');
  });

  it.each([
    ['Idle', IDLE],
    ['Active', { ...IDLE, is_running: true }],
  ])('leaves the dot still while %s', (_text, status) => {
    renderWithProviders(<StatusPill status={status} />);

    expect(dot()).toHaveAttribute('data-processing', 'false');
  });

  it('gives a running instance a different colour than an idle one', () => {
    const { unmount } = renderWithProviders(<StatusPill status={IDLE} />);
    const idleColor = dot().style.getPropertyValue('--ev-dot');
    unmount();

    renderWithProviders(<StatusPill status={{ ...IDLE, is_running: true }} />);

    expect(dot().style.getPropertyValue('--ev-dot')).not.toBe(idleColor);
  });
});

describe('StatusChip', () => {
  it('draws a dot of its own by default', () => {
    renderWithProviders(<StatusChip variant="good">Active</StatusChip>);

    expect(dot()).toBeInTheDocument();
  });

  it('takes a dot it is given instead', () => {
    renderWithProviders(
      <StatusChip variant="good" dot={<span data-custom />}>
        Active
      </StatusChip>
    );

    expect(document.querySelector('[data-custom]')).toBeInTheDocument();
    expect(document.querySelectorAll('.ev-status-dot')).toHaveLength(0);
  });

  it('drops the dot when told to', () => {
    renderWithProviders(
      <StatusChip variant="idle" dot={null}>
        Idle
      </StatusChip>
    );

    expect(document.querySelectorAll('.ev-status-dot')).toHaveLength(0);
    expect(screen.getByText('Idle')).toBeInTheDocument();
  });
});

/**
 * A dot may be drawn before the status of its instance has been read,
 * and it has to look like something rather than nothing.
 */
describe('StatusDot', () => {
  it('falls back to the idle colour when no status is known', () => {
    renderWithProviders(<StatusDot status={undefined} />);

    expect(dot().style.getPropertyValue('--ev-dot')).not.toBe('');
  });

  it('does not animate without a status, however it is asked', () => {
    renderWithProviders(<StatusDot status={undefined} pulse />);

    expect(dot()).toHaveAttribute('data-processing', 'false');
  });

  it('animates only when asked to', () => {
    const starting = { ...IDLE, is_initializing: true };
    const { unmount } = renderWithProviders(<StatusDot status={starting} />);

    expect(dot()).toHaveAttribute('data-processing', 'false');
    unmount();

    renderWithProviders(<StatusDot status={starting} pulse />);

    expect(dot()).toHaveAttribute('data-processing', 'true');
  });
});
