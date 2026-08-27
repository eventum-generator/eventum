import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { InstanceState } from './InstanceState';
import { GeneratorStats } from '@/api/routes/generators/schemas';
import { renderWithProviders } from '@/test/render';

function stats(values: {
  produced?: number;
  produceFailed?: number;
  dropped?: number;
  generated?: number;
  written?: number;
  outputs?: { write_failed: number; format_failed: number }[];
}): GeneratorStats {
  return {
    id: 'web',
    start_time: '2026-08-20T10:00:00Z',
    resources: {
      thread_count: 1,
      cpu_seconds: 0,
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
      produced: values.produced ?? 0,
      produce_failed: values.produceFailed ?? 0,
      dropped: values.dropped ?? 0,
    },
    output: (values.outputs ?? []).map((output, index) => ({
      plugin_name: 'file',
      plugin_id: index,
      written: 0,
      ...output,
    })),
    total_generated: values.generated ?? 0,
    total_written: values.written ?? 0,
    uptime: 60,
    input_eps: 0,
    output_eps: 0,
  } as GeneratorStats;
}

function setup(
  values: Parameters<typeof stats>[0] = {},
  rates: { inputEps?: number; outputEps?: number } = {}
) {
  renderWithProviders(
    <InstanceState
      stats={stats(values)}
      inputEps={rates.inputEps ?? 5}
      outputEps={rates.outputEps ?? 4}
    />
  );
}

/** The figure of one reading, by the name of the reading. */
function reading(label: string): HTMLElement {
  const found = document.querySelector(`[data-reading="${label}"]`);

  if (found === null) {
    throw new Error(`the strip drew no ${label} reading`);
  }

  return found as HTMLElement;
}

/**
 * The strip reports what the instance moves now and what it has moved
 * in total. The failure count is summed across every stage and every
 * output plugin - a count that only looked at the first plugin would
 * read as healthy while a second one fails everything.
 */
describe('InstanceState', () => {
  it('reports the rate in and out', () => {
    setup({}, { inputEps: 12, outputEps: 10 });

    expect(reading('input')).toHaveTextContent(/^12(\.\d+)?\/s$/);
    expect(reading('output')).toHaveTextContent(/^10(\.\d+)?\/s$/);
  });

  it('reports the totals of the run', () => {
    setup({ generated: 1200, produced: 1150, written: 1100 });

    expect(screen.getByText(/1\.2K generated/)).toBeInTheDocument();
    expect(screen.getByText(/1\.2K produced/)).toBeInTheDocument();
    expect(screen.getByText(/1\.1K written/)).toBeInTheDocument();
  });

  it('reports what the run dropped, apart from what it wrote', () => {
    setup({ dropped: 20 });

    expect(reading('dropped')).toHaveTextContent(/^20$/);
  });

  it('sums the failures of every stage', () => {
    setup({
      produceFailed: 2,
      outputs: [
        { write_failed: 3, format_failed: 1 },
        { write_failed: 4, format_failed: 0 },
      ],
    });

    expect(reading('failed')).toHaveTextContent(/^10$/);
  });

  it('reports no failures as none rather than as unknown', () => {
    setup();

    expect(reading('failed')).toHaveTextContent(/^0$/);
  });

  it('colours the failure total once something failed', () => {
    setup({ produceFailed: 1 });

    expect(reading('failed').getAttribute('style') ?? '').toContain('red');
  });

  it('leaves it uncoloured while nothing failed', () => {
    setup();

    expect(reading('failed').getAttribute('style') ?? '').not.toContain('red');
  });

  it('reads an instance with no output plugin as no output failures', () => {
    setup({ produceFailed: 3 });

    expect(reading('failed')).toHaveTextContent(/^3$/);
  });
});
