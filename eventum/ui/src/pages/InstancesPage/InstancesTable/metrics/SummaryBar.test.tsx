import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { SummaryBar } from './SummaryBar';
import { GeneratorStats } from '@/api/routes/generators/schemas';
import { renderWithProviders } from '@/test/render';

function stats(overrides: Partial<GeneratorStats> = {}): GeneratorStats {
  return {
    id: 'web',
    start_time: '2026-08-20T10:00:00Z',
    resources: {
      thread_count: 4,
      cpu_seconds: 1,
      run_delay_seconds: 0,
      disk_read_bytes: 0,
      disk_written_bytes: 0,
      network_sent_bytes: 0,
      network_received_bytes: 0,
      queues: {
        timestamps: { size: 0, maxsize: 10, size_bytes: 0, max_bytes: null },
        events: { size: 0, maxsize: 10, size_bytes: 0, max_bytes: null },
      },
    },
    input: [],
    event: {
      plugin_name: 'template',
      plugin_id: 1,
      produced: 0,
      produce_failed: 0,
      dropped: 0,
    },
    output: [],
    total_generated: 1200,
    total_written: 1100,
    uptime: 65,
    input_eps: 12.345,
    output_eps: 11.987,
    ...overrides,
  } as GeneratorStats;
}

function setup(overrides: Partial<GeneratorStats> = {}) {
  renderWithProviders(<SummaryBar stats={stats(overrides)} />);
}

/**
 * The bar sits above the metrics of one instance and names what the run
 * has done so far. The uptime is the derived figure: it names the two
 * largest units that apply, so a run of days does not read in seconds.
 */
describe('SummaryBar', () => {
  it('names the instance', () => {
    setup();

    expect(screen.getByText('web')).toBeInTheDocument();
  });

  it('reports the totals of the run', () => {
    setup();

    expect(screen.getByText('1200')).toBeInTheDocument();
    expect(screen.getByText('1100')).toBeInTheDocument();
  });

  it('reports the rates to two decimals, so a slow run is not zero', () => {
    setup({ input_eps: 0.004, output_eps: 0 });

    expect(screen.getAllByText('0.00').length).toBeGreaterThan(0);
  });

  it('reports both rates', () => {
    setup();

    expect(screen.getByText('12.35')).toBeInTheDocument();
    expect(screen.getByText('11.99')).toBeInTheDocument();
  });

  it.each([
    [45, /45s/],
    [65, /1m 05s/],
    [3725, /1h 2m 5s/],
    [90_000, /1d 1h 0m/],
  ])('reads an uptime of %i seconds as %s', (uptime, expected) => {
    setup({ uptime });

    expect(screen.getByText(expected)).toBeInTheDocument();
  });

  it('says when the run started', () => {
    setup();

    expect(screen.getByText(/^Started /)).toBeInTheDocument();
  });

  it('reports a run that has just started rather than nothing', () => {
    setup({ uptime: 0, total_generated: 0, total_written: 0 });

    expect(screen.getByText(/0s/)).toBeInTheDocument();
    expect(screen.getAllByText('0').length).toBeGreaterThan(0);
  });
});
