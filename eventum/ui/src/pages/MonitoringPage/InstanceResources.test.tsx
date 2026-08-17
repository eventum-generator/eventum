import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { InstanceResources } from './InstanceResources';
import { InstanceUsage, UsagePoint } from './history';
import { renderWithProviders } from '@/test/render';

const IDLE: InstanceUsage = {
  cpuSeconds: 0,
  runDelaySeconds: 0,
  diskWrite: 0,
  netSent: 0,
  threads: 5,
  queueBytes: 0,
  queueMaxBytes: 134_217_728,
};

const POLLS: UsagePoint[] = [
  { t: 1000, usage: { busy: IDLE, calm: IDLE } },
  {
    t: 3000,
    usage: {
      busy: {
        ...IDLE,
        cpuSeconds: 1.5,
        runDelaySeconds: 0.5,
        diskWrite: 4 * 1024 * 1024,
        netSent: 2 * 1024 * 1024,
        threads: 8,
        queueBytes: 96 * 1024 * 1024,
      },
      calm: { ...IDLE, cpuSeconds: 0.02 },
    },
  },
];

describe('InstanceResources', () => {
  it('reports what each instance occupies, heaviest first', () => {
    renderWithProviders(<InstanceResources usage={POLLS} />);

    const ids = screen
      .getAllByRole('row')
      .slice(1)
      .map((row) => row.textContent);
    expect(ids[0]).toContain('busy');
    expect(ids[1]).toContain('calm');

    expect(screen.getByText('75.0%')).toBeInTheDocument();
    expect(screen.getByText('25.0%')).toBeInTheDocument();
    expect(screen.getByText('8')).toBeInTheDocument();
    expect(screen.getByText('2MB/s')).toBeInTheDocument();
    expect(screen.getByText('1MB/s')).toBeInTheDocument();
    expect(screen.getByText('96MB / 128MB')).toBeInTheDocument();
  });

  it('waits for a second poll before reporting rates', () => {
    renderWithProviders(<InstanceResources usage={POLLS.slice(0, 1)} />);

    expect(screen.getByText('Collecting data...')).toBeInTheDocument();
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
  });
});
