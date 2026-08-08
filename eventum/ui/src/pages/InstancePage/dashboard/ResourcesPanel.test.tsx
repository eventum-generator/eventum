import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { ResourcesPanel } from './ResourcesPanel';
import { ResourcesStats } from '@/api/routes/generators/schemas';
import { renderWithProviders } from '@/test/render';

const RESOURCES: ResourcesStats = {
  thread_count: 5,
  cpu_seconds: 75,
  queues: {
    timestamps: { size: 3, maxsize: 10 },
    events: { size: 10, maxsize: 10 },
  },
};

describe('ResourcesPanel', () => {
  it('reports the load of the instance', () => {
    renderWithProviders(
      <ResourcesPanel resources={RESOURCES} cpuPercent={42.35} />
    );

    expect(screen.getByText('42.4%')).toBeInTheDocument();
    expect(screen.getByText('1m 15s')).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument();
  });

  it('reports the fill level of each pipeline queue', () => {
    renderWithProviders(
      <ResourcesPanel resources={RESOURCES} cpuPercent={0} />
    );

    expect(screen.getByText('3 / 10')).toBeInTheDocument();
    expect(screen.getByText('10 / 10')).toBeInTheDocument();

    const timestamps = screen.getByLabelText('Timestamps queue fill');
    const events = screen.getByLabelText('Events queue fill');

    expect(timestamps).toHaveAttribute('aria-valuenow', '30');
    expect(events).toHaveAttribute('aria-valuenow', '100');
  });
});
