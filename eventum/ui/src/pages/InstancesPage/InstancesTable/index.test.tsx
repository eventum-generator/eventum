import { RowSelectionState } from '@tanstack/react-table';
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { InstancesTable } from './index';
import {
  GeneratorStats,
  GeneratorStatus,
  GeneratorsInfo,
} from '@/api/routes/generators/schemas';
import { renderWithProviders } from '@/test/render';

vi.mock('@/api/hooks/useGenerators');
vi.mock('@/api/hooks/useStartup');

const IDLE: GeneratorStatus = {
  is_initializing: false,
  is_running: false,
  is_ended_up: false,
  is_ended_up_successfully: false,
  is_stopping: false,
};

const RUNNING: GeneratorStatus = { ...IDLE, is_running: true };
const STOPPING: GeneratorStatus = { ...IDLE, is_stopping: true };
const FINISHED: GeneratorStatus = {
  ...IDLE,
  is_ended_up: true,
  is_ended_up_successfully: true,
};
const FAILED: GeneratorStatus = { ...IDLE, is_ended_up: true };

const DATA: GeneratorsInfo = [
  {
    id: 'api-live',
    path: 'api/generator.yml',
    status: RUNNING,
    start_time: '2026-01-01T00:00:00+00:00',
  },
  { id: 'web-idle', path: 'web/generator.yml', status: IDLE, start_time: null },
  {
    id: 'web-done',
    path: 'web/generator.yml',
    status: FINISHED,
    start_time: '2026-01-01T00:00:00+00:00',
  },
];

function stats(overrides: Partial<GeneratorStats> = {}): GeneratorStats {
  return {
    id: 'api-live',
    start_time: '2026-01-01T00:00:00+00:00',
    uptime: 60,
    input_eps: 10,
    output_eps: 12,
    total_generated: 600,
    total_written: 590,
    resources: {
      thread_count: 2,
      cpu_seconds: 6,
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
    input: [{ plugin_name: 'timer', plugin_id: 1, generated: 600 }],
    event: {
      plugin_name: 'template',
      plugin_id: 2,
      produced: 600,
      produce_failed: 0,
      dropped: 0,
    },
    output: [
      {
        plugin_name: 'file',
        plugin_id: 3,
        written: 590,
        write_failed: 3,
        format_failed: 1,
      },
    ],
    ...overrides,
  } as GeneratorStats;
}

interface Options {
  data?: GeneratorsInfo;
  instancesFilter?: string;
  projectNameFilter?: string;
  statusMode?: 'all' | 'active' | 'inactive';
  statsById?: Record<string, GeneratorStats>;
}

function setup(options: Options = {}) {
  const Host = () => {
    const [selection, setSelection] = useState<RowSelectionState>({});

    return (
      <InstancesTable
        data={options.data ?? DATA}
        instancesFilter={options.instancesFilter}
        projectNameFilter={options.projectNameFilter}
        statusMode={options.statusMode}
        statsById={options.statsById}
        rowSelection={selection}
        onRowSelectionChange={setSelection}
      />
    );
  };

  renderWithProviders(
    <MemoryRouter>
      <Host />
    </MemoryRouter>
  );

  return userEvent.setup();
}

/** The ids of the rows the table is showing, in order. */
function shownIds(): string[] {
  return screen
    .getAllByRole('row')
    .slice(1)
    .map((row) => within(row).getAllByRole('cell')[1]?.textContent ?? '')
    .filter((id) => id !== '');
}

beforeEach(() => {
  vi.clearAllMocks();
});

/**
 * The table is the list of what this instance runs, and every row is
 * read from two sources: what the manager knows about the generator, and
 * the stats it only has while running. So a row of an instance at rest
 * has to draw the columns it has no figures for without pretending they
 * are zero, and the filters above the table have to agree on what
 * "active" means - a stopping instance is still live.
 */
describe('InstancesTable', () => {
  it('lists every instance by name', () => {
    setup();

    expect(shownIds()).toEqual(['api-live', 'web-done', 'web-idle']);
  });

  it('names the project each instance runs', () => {
    setup();

    expect(screen.getAllByText('web')).toHaveLength(2);
    expect(screen.getByText('api')).toBeInTheDocument();
  });

  it('says what each instance is doing', () => {
    setup();

    expect(screen.getByText('Active')).toBeInTheDocument();
    expect(screen.getByText('Idle')).toBeInTheDocument();
    expect(screen.getByText('Finished')).toBeInTheDocument();
  });

  it('names a run that ended badly as such', () => {
    setup({
      data: [
        {
          id: 'web-failed',
          path: 'web/generator.yml',
          status: FAILED,
          start_time: '2026-01-01T00:00:00+00:00',
        },
      ],
    });

    expect(screen.getByText('Failed')).toBeInTheDocument();
  });

  it('keeps the instances still on the move among the active ones', () => {
    setup({
      data: [
        {
          id: 'web-stopping',
          path: 'web/generator.yml',
          status: STOPPING,
          start_time: '2026-01-01T00:00:00+00:00',
        },
      ],
      statusMode: 'active',
    });

    // A stopping instance is still running something, so hiding it under
    // "active" would lose it from both lists.
    expect(shownIds()).toEqual(['web-stopping']);
  });

  it('narrows to the instances that are running', () => {
    setup({ statusMode: 'active' });

    expect(shownIds()).toEqual(['api-live']);
  });

  it('narrows to the instances at rest', () => {
    setup({ statusMode: 'inactive' });

    expect(shownIds()).toEqual(['web-done', 'web-idle']);
  });

  it('narrows by the name of the instance', () => {
    setup({ instancesFilter: 'web' });

    expect(shownIds()).toEqual(['web-done', 'web-idle']);
  });

  it('narrows by the project the instance runs', () => {
    setup({ projectNameFilter: 'api' });

    expect(shownIds()).toEqual(['api-live']);
  });

  it('says so when the filters leave nothing', () => {
    setup({ instancesFilter: 'nothing-matches-this' });

    expect(
      screen.getByText('No instances match your filters')
    ).toBeInTheDocument();
  });

  it('draws the figures of a running instance', () => {
    setup({ statsById: { 'api-live': stats() } });

    // Flow, errors and written come from the stats, and errors are the
    // write and format failures together.
    expect(screen.getByText('590')).toBeInTheDocument();
    expect(screen.getByText('4')).toBeInTheDocument();
  });

  it('leaves the figures of an instance at rest empty', () => {
    setup({ data: [DATA[1]!] });

    // There are no stats for an instance that is not running, and a zero
    // would read as "it wrote nothing" rather than "it never ran".
    const row = screen.getAllByRole('row')[1]!;

    expect(within(row).getAllByText('-').length).toBeGreaterThan(0);
  });

  it('sorts by a column when its header is used', async () => {
    const user = setup();

    await user.click(screen.getByRole('button', { name: 'Sort by instance' }));

    expect(shownIds()).toEqual(['web-idle', 'web-done', 'api-live']);
  });

  it('selects a row for the actions above the table', async () => {
    const user = setup();

    const row = screen.getAllByRole('row')[1]!;
    await user.click(within(row).getByRole('checkbox'));

    expect(within(row).getByRole('checkbox')).toBeChecked();
  });

  it('selects every row at once', async () => {
    const user = setup();

    await user.click(screen.getByRole('checkbox', { name: 'Select all' }));

    for (const row of screen.getAllByRole('row').slice(1)) {
      expect(within(row).getByRole('checkbox')).toBeChecked();
    }
  });
});
