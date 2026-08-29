import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import { InstanceDetails } from './InstanceDetails';
import { InstanceUsageRow } from './history';
import { GeneratorStats } from '@/api/routes/generators/schemas';
import { renderWithProviders } from '@/test/render';

const ROW: InstanceUsageRow = {
  id: 'web',
  cpuPercent: 12.3,
  waitPercent: 1.5,
  diskWriteBps: 2048,
  netSentBps: 4096,
  threads: 3,
  outputEps: 120,
  failEps: 0,
  queueSize: 2,
  queueMaxsize: 10,
  queueBytes: 1024,
  queueMaxBytes: 4096,
  queuePercent: 25,
} as InstanceUsageRow;

const STATS = {
  id: 'web',
  start_time: '2026-01-01T00:00:00+00:00',
  uptime: 3600,
  input_eps: 100,
  output_eps: 120,
  total_generated: 1000,
  total_written: 990,
  resources: {
    thread_count: 3,
    cpu_seconds: 12,
    run_delay_seconds: 0.1,
    disk_read_bytes: 0,
    disk_written_bytes: 2048,
    network_sent_bytes: 4096,
    network_received_bytes: 0,
    queues: {
      timestamps: { size: 1, maxsize: 10, size_bytes: 16, max_bytes: null },
      events: { size: 2, maxsize: 10, size_bytes: 1024, max_bytes: 4096 },
    },
  },
  input: [{ plugin_name: 'timer', plugin_id: 1, generated: 1000 }],
  event: {
    plugin_name: 'template',
    plugin_id: 2,
    produced: 995,
    produce_failed: 0,
    dropped: 5,
  },
  output: [
    {
      plugin_name: 'file',
      plugin_id: 3,
      written: 990,
      write_failed: 0,
      format_failed: 0,
    },
  ],
} as GeneratorStats;

interface Options {
  row?: InstanceUsageRow;
  stats?: GeneratorStats;
  id?: string | null;
  onClose?: () => void;
}

function setup(overrides: Options = {}) {
  // Each of these is meaningful when absent - an instance that stopped
  // has no stats - so what was passed is read from the keys rather than
  // from the values.
  renderWithProviders(
    <MemoryRouter>
      <InstanceDetails
        id={'id' in overrides ? (overrides.id ?? null) : 'web'}
        row={'row' in overrides ? overrides.row : ROW}
        stats={'stats' in overrides ? overrides.stats : STATS}
        onClose={overrides.onClose ?? vi.fn()}
      />
    </MemoryRouter>
  );
}

/**
 * The drawer answers one question about one instance: is it well. It
 * opens on the four figures that say so, and the ones that mean trouble
 * are coloured rather than only listed - a failure rate of nothing and a
 * failure rate of ten look the same in plain text.
 */
describe('InstanceDetails', () => {
  it('opens on the instance it was given', () => {
    setup();

    expect(screen.getByText('web')).toBeInTheDocument();
    expect(screen.getByText(/running for/)).toBeInTheDocument();
  });

  it('stays closed while no instance is picked', () => {
    setup({ id: null });

    expect(screen.queryByText('written now')).toBeNull();
  });

  it('says an instance it has no stats for is gone', () => {
    setup({ stats: undefined });

    // The drawer outlives the run it was opened on, so it has to say so
    // rather than draw zeroes.
    expect(
      screen.getByText('The instance is no longer running.')
    ).toBeInTheDocument();
  });

  it('reports what the instance is doing right now', () => {
    setup();

    expect(screen.getByText('written now')).toBeInTheDocument();
    expect(screen.getByText('12.3%')).toBeInTheDocument();
    expect(screen.getByText('25%')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
  });

  it('names every plugin of the pipeline with what it moved', () => {
    setup();

    expect(screen.getByText('timer')).toBeInTheDocument();
    expect(screen.getByText('template')).toBeInTheDocument();
    expect(screen.getByText('file')).toBeInTheDocument();
  });

  it('names what the event plugin dropped', () => {
    setup();

    expect(screen.getByText('dropped')).toBeInTheDocument();
  });

  it('says nothing about failures there were none of', () => {
    setup();

    expect(screen.queryByText('failed to produce')).toBeNull();
    expect(screen.queryByText('failed to write or format')).toBeNull();
  });

  it('names a failure of the event plugin', () => {
    setup({
      stats: {
        ...STATS,
        event: { ...STATS.event, produce_failed: 4 },
      } as GeneratorStats,
    });

    expect(screen.getByText('failed to produce')).toBeInTheDocument();
  });

  it('names a failure of an output plugin', () => {
    setup({
      stats: {
        ...STATS,
        output: [{ ...STATS.output[0]!, write_failed: 2 }],
      } as GeneratorStats,
    });

    expect(screen.getByText('failed to write or format')).toBeInTheDocument();
  });

  it('reports the fill of both queues', () => {
    setup();

    expect(
      screen.getByRole('progressbar', { name: 'Timestamps queue fill' })
    ).toBeInTheDocument();
    expect(
      screen.getByRole('progressbar', { name: 'Events queue fill' })
    ).toBeInTheDocument();
  });

  it('names the byte limit of a queue that has one', () => {
    setup();

    // The events queue is bounded in bytes as well as in batches, and
    // both bounds are what a full queue is read against.
    expect(screen.getByText(/1KB \/ 4KB/)).toBeInTheDocument();
  });

  it('leaves out a byte limit that was lifted', () => {
    setup();

    // The timestamps queue carries no byte limit, so its reading is the
    // size alone.
    expect(screen.getByText(/1 \/ 10 · 16B$/)).toBeInTheDocument();
  });

  it('closes on the control the drawer draws for it', async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();

    setup({ onClose });

    await user.click(
      screen.getByRole('button', { name: 'Close instance details' })
    );

    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
