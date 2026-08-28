import { describe, expect, it } from 'vitest';

import { aggregateFlow, formatUptime } from './metrics';
import { GeneratorStats } from '@/api/routes/generators/schemas';

function stats(values: {
  generated?: number;
  written?: number;
  produced?: number;
  dropped?: number;
  produceFailed?: number;
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
    uptime: 1,
    input_eps: 0,
    output_eps: 0,
  } as GeneratorStats;
}

/**
 * The monitoring strip reports the fleet as one pipeline, so every
 * counter is a sum across generators - and across the output plugins
 * inside each of them, which is where a single-plugin assumption would
 * lose failures.
 */
describe('aggregateFlow', () => {
  it('sums the counters of every generator', () => {
    const agg = aggregateFlow([
      stats({ generated: 10, written: 8, produced: 9, dropped: 1 }),
      stats({ generated: 20, written: 15, produced: 18, dropped: 2 }),
    ]);

    expect(agg.generated).toBe(30);
    expect(agg.written).toBe(23);
    expect(agg.produced).toBe(27);
    expect(agg.dropped).toBe(3);
  });

  it('sums the failures of every output plugin, not just the first', () => {
    const agg = aggregateFlow([
      stats({
        outputs: [
          { write_failed: 1, format_failed: 2 },
          { write_failed: 3, format_failed: 4 },
        ],
      }),
    ]);

    expect(agg.writeFailed).toBe(4);
    expect(agg.formatFailed).toBe(6);
  });

  it('keeps the event failures apart from the output ones', () => {
    const agg = aggregateFlow([
      stats({
        produceFailed: 5,
        outputs: [{ write_failed: 1, format_failed: 0 }],
      }),
    ]);

    expect(agg.produceFailed).toBe(5);
    expect(agg.writeFailed).toBe(1);
  });

  it('reads an empty fleet as zeroes rather than as nothing', () => {
    expect(aggregateFlow([])).toEqual({
      generated: 0,
      produced: 0,
      written: 0,
      dropped: 0,
      produceFailed: 0,
      writeFailed: 0,
      formatFailed: 0,
    });
  });

  it('reads a generator with no output plugin as no output failures', () => {
    const agg = aggregateFlow([stats({ written: 5 })]);

    expect(agg.writeFailed).toBe(0);
    expect(agg.written).toBe(5);
  });
});

/**
 * The uptime is read at a glance, so it names the two largest units
 * that apply and stops there.
 */
describe('formatUptime', () => {
  it.each([
    [0, '0s'],
    [45, '45s'],
    [59, '59s'],
    [60, '1m'],
    [3599, '59m'],
    [3600, '1h 0m'],
    [3660, '1h 1m'],
    [86_399, '23h 59m'],
    [86_400, '1d 0h'],
    [90_000, '1d 1h'],
  ])('reads %i seconds as %s', (seconds, expected) => {
    expect(formatUptime(seconds)).toBe(expected);
  });

  it('reads a negative uptime as none rather than as a negative one', () => {
    expect(formatUptime(-10)).toBe('0s');
  });

  it('drops the fraction of a second', () => {
    expect(formatUptime(45.9)).toBe('45s');
  });
});
