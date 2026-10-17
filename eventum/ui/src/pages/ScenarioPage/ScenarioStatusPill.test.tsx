import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { ScenarioStatusPill } from './ScenarioStatusPill';
import { ScenarioStatusCounts } from './scenario-status';
import { renderWithProviders } from '@/test/render';

const NONE: ScenarioStatusCounts = {
  total: 0,
  stuck: 0,
  running: 0,
  initializing: 0,
  stopping: 0,
  inactive: 0,
};

/**
 * The pill is the one word a scenario is summed up by, so the state that
 * needs a restart of Eventum to clear has to win over the rest.
 */
describe('ScenarioStatusPill', () => {
  it.each([
    ['Stuck', { total: 2, stuck: 1, running: 1 }],
    ['Running', { total: 2, running: 1, inactive: 1 }],
    ['Starting', { total: 1, initializing: 1 }],
    ['Stopping', { total: 1, stopping: 1 }],
    ['Inactive', { total: 1, inactive: 1 }],
  ])('reads as %s', (label, counts) => {
    renderWithProviders(<ScenarioStatusPill counts={{ ...NONE, ...counts }} />);

    expect(screen.getByText(label)).toBeInTheDocument();
  });
});
