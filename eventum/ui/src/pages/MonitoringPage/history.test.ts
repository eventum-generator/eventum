import { describe, expect, it } from 'vitest';

import {
  FlowPoint,
  InstanceUsage,
  LoadPoint,
  OTHER_BAND,
  UsagePoint,
  instanceBands,
  instanceUsageRows,
  stageData,
} from './history';

const IDLE: InstanceUsage = {
  cpuSeconds: 0,
  runDelaySeconds: 0,
  diskWrite: 0,
  netSent: 0,
  threads: 5,
  written: 0,
  failed: 0,
  queueSize: 0,
  queueMaxsize: 10,
  queueBytes: 0,
  queueMaxBytes: null,
};

function poll(t: number, usage: Record<string, InstanceUsage>): UsagePoint {
  return { t, usage };
}

describe('instanceUsageRows', () => {
  it('derives the share of a core from two polls', () => {
    const rows = instanceUsageRows([
      poll(1000, { a: { ...IDLE, cpuSeconds: 1, runDelaySeconds: 0.2 } }),
      poll(3000, { a: { ...IDLE, cpuSeconds: 2.5, runDelaySeconds: 0.4 } }),
    ]);

    // 1.5 s of processor time and 0.2 s of waiting over 2 s of wall clock.
    expect(rows).toHaveLength(1);
    expect(rows[0]?.cpuPercent).toBeCloseTo(75);
    expect(rows[0]?.waitPercent).toBeCloseTo(10);
  });

  it('derives byte rates and carries the current figures', () => {
    const rows = instanceUsageRows([
      poll(1000, { a: IDLE }),
      poll(3000, {
        a: {
          ...IDLE,
          diskWrite: 4096,
          netSent: 2048,
          threads: 7,
          queueBytes: 512,
          queueMaxBytes: 65_536,
        },
      }),
    ]);

    expect(rows[0]?.diskWriteBps).toBeCloseTo(2048);
    expect(rows[0]?.netSentBps).toBeCloseTo(1024);
    expect(rows[0]?.threads).toBe(7);
    expect(rows[0]?.queueBytes).toBe(512);
    expect(rows[0]?.queueMaxBytes).toBe(65_536);
  });

  it('ranks the heaviest instance first', () => {
    const rows = instanceUsageRows([
      poll(1000, { light: IDLE, heavy: IDLE }),
      poll(2000, {
        light: { ...IDLE, cpuSeconds: 0.1 },
        heavy: { ...IDLE, cpuSeconds: 0.9 },
      }),
    ]);

    expect(rows.map((row) => row.id)).toEqual(['heavy', 'light']);
  });

  it('counts nothing for an instance the earlier poll did not hold', () => {
    const rows = instanceUsageRows([
      poll(1000, { a: IDLE }),
      poll(2000, { a: IDLE, b: { ...IDLE, cpuSeconds: 100 } }),
    ]);

    const started = rows.find((row) => row.id === 'b');
    expect(started?.cpuPercent).toBe(0);
    expect(started?.threads).toBe(5);
  });

  it('has nothing to derive from a single poll', () => {
    expect(instanceUsageRows([poll(1000, { a: IDLE })])).toEqual([]);
    expect(instanceUsageRows([])).toEqual([]);
  });

  it('derives what an instance writes and what it fails to', () => {
    const rows = instanceUsageRows([
      poll(1000, { a: IDLE }),
      poll(3000, { a: { ...IDLE, written: 600, failed: 20 } }),
    ]);

    expect(rows[0]?.outputEps).toBeCloseTo(300);
    expect(rows[0]?.failEps).toBeCloseTo(10);
  });

  it('takes the queue fill from whichever limit it is closer to', () => {
    const [batches] = instanceUsageRows([
      poll(1000, { a: IDLE }),
      poll(2000, { a: { ...IDLE, queueSize: 9, queueMaxsize: 10 } }),
    ]);
    const [held] = instanceUsageRows([
      poll(1000, { a: IDLE }),
      poll(2000, {
        a: { ...IDLE, queueSize: 1, queueBytes: 96, queueMaxBytes: 128 },
      }),
    ]);

    expect(batches?.queuePercent).toBeCloseTo(90);
    expect(held?.queuePercent).toBeCloseTo(75);
  });

  it('reports no fill for a queue held back by neither limit', () => {
    const rows = instanceUsageRows([
      poll(1000, { a: { ...IDLE, queueMaxsize: 0 } }),
      poll(2000, { a: { ...IDLE, queueMaxsize: 0, queueBytes: 4096 } }),
    ]);

    expect(rows[0]?.queuePercent).toBe(0);
  });
});

function load(t: number, written: Record<string, number>): LoadPoint {
  return { t, time: '', written };
}

describe('instanceBands', () => {
  it('keeps every instance while they fit the chart', () => {
    const { ids, rows } = instanceBands(
      [load(1000, { a: 0, b: 0 }), load(3000, { a: 200, b: 100 })],
      6
    );

    expect(ids).toEqual(['a', 'b']);
    expect(rows[0]?.rates).toEqual({ a: 100, b: 50 });
  });

  it('sums everything past the top into one band', () => {
    const { ids, rows } = instanceBands(
      [
        load(1000, { a: 0, b: 0, c: 0, d: 0 }),
        load(3000, { a: 400, b: 300, c: 200, d: 100 }),
      ],
      2
    );

    expect(ids).toEqual(['a', 'b', OTHER_BAND]);
    // The two smaller instances land in one band: 100/s and 50/s.
    expect(rows[0]?.rates[OTHER_BAND]).toBeCloseTo(150);
  });
});

function flowPoint(t: number, values: Partial<FlowPoint>): FlowPoint {
  return {
    t,
    generated: 0,
    produced: 0,
    written: 0,
    dropped: 0,
    produceFailed: 0,
    writeFailed: 0,
    formatFailed: 0,
    ...values,
  };
}

describe('stageData', () => {
  it('turns the cumulative counter of every stage into its rate', () => {
    const rows = stageData([
      flowPoint(1000, {}),
      flowPoint(3000, { generated: 600, produced: 400, written: 200 }),
    ]);

    expect(rows).toHaveLength(1);
    expect(rows[0]?.input).toBeCloseTo(300);
    expect(rows[0]?.event).toBeCloseTo(200);
    expect(rows[0]?.output).toBeCloseTo(100);
  });
});
