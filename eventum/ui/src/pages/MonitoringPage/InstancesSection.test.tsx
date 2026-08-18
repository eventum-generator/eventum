import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { InstancesSection } from './InstancesSection';
import { InstanceUsageRow } from './history';
import { GeneratorStats } from '@/api/routes/generators/schemas';
import { renderWithProviders } from '@/test/render';

const ROW: InstanceUsageRow = {
  id: 'calm',
  cpuPercent: 2,
  waitPercent: 0,
  diskWriteBps: 0,
  netSentBps: 0,
  threads: 5,
  outputEps: 100,
  failEps: 0,
  queueSize: 0,
  queueMaxsize: 10,
  queueBytes: 0,
  queueMaxBytes: 134_217_728,
  queuePercent: 0,
};

const ROWS: InstanceUsageRow[] = [
  { ...ROW, id: 'failing', failEps: 3 },
  { ...ROW, id: 'stuffed', queuePercent: 100 },
  { ...ROW, id: 'quiet', outputEps: 0 },
  ROW,
];

const STATS: GeneratorStats[] = [
  {
    id: 'failing',
    start_time: '2026-08-17T10:00:00Z',
    resources: {
      thread_count: 5,
      cpu_seconds: 30,
      run_delay_seconds: 0.5,
      disk_read_bytes: 1024,
      disk_written_bytes: 2048,
      network_sent_bytes: 512,
      network_received_bytes: 0,
      queues: {
        timestamps: { size: 1, maxsize: 10, size_bytes: 64, max_bytes: null },
        events: {
          size: 2,
          maxsize: 10,
          size_bytes: 1024,
          max_bytes: 134_217_728,
        },
      },
    },
    input: [{ plugin_name: 'cron', plugin_id: 1, generated: 5000 }],
    event: {
      plugin_name: 'template',
      plugin_id: 1,
      produced: 4900,
      produce_failed: 10,
      dropped: 90,
    },
    output: [
      {
        plugin_name: 'tcp',
        plugin_id: 1,
        written: 4800,
        write_failed: 100,
        format_failed: 0,
      },
    ],
    total_generated: 5000,
    total_written: 4800,
    uptime: 120,
    input_eps: 41.6,
    output_eps: 40,
  },
];

function render() {
  renderWithProviders(
    <MemoryRouter>
      <InstancesSection
        rows={ROWS}
        load={[]}
        flow={[]}
        stats={STATS}
        points={30}
      />
    </MemoryRouter>
  );
}

function ids(): string[] {
  return screen
    .getAllByRole('row')
    .slice(1)
    .map((row) => row.textContent ?? '');
}

describe('InstancesSection', () => {
  it('lists every running instance', () => {
    render();

    expect(screen.getByText('4 running')).toBeInTheDocument();
    expect(ids()).toHaveLength(4);
  });

  it('keeps only the instances a quick filter asks for', async () => {
    const user = userEvent.setup();
    render();

    await user.click(screen.getByText('Failing'));
    expect(ids()).toHaveLength(1);
    expect(ids()[0]).toContain('failing');
    expect(screen.getByText('1 of 4 running')).toBeInTheDocument();

    await user.click(screen.getByText('At the limit'));
    expect(ids()[0]).toContain('stuffed');

    await user.click(screen.getByText('Idle'));
    expect(ids()[0]).toContain('quiet');
  });

  it('narrows the list by id', async () => {
    const user = userEvent.setup();
    render();

    await user.type(screen.getByPlaceholderText('Search instances'), 'ca');

    expect(ids()).toHaveLength(1);
    expect(ids()[0]).toContain('calm');
  });

  it('says so when the filter matches nothing', async () => {
    const user = userEvent.setup();
    render();

    await user.type(screen.getByPlaceholderText('Search instances'), 'nothing');

    expect(
      screen.getByText('No instances match the filter')
    ).toBeInTheDocument();
  });

  it('opens the details of the instance a row belongs to', async () => {
    const user = userEvent.setup();
    render();

    await user.click(screen.getByText('failing'));

    expect(
      await screen.findByText('Open the instance page')
    ).toBeInTheDocument();
    expect(screen.getByText('cron')).toBeInTheDocument();
    expect(screen.getByText('5K generated')).toBeInTheDocument();
    expect(screen.getByText('failed to write or format')).toBeInTheDocument();
  });
});
