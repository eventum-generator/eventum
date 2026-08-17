import { describe, expect, it } from 'vitest';

import { InstanceUsage, UsagePoint, instanceUsageRows } from './history';

const IDLE: InstanceUsage = {
  cpuSeconds: 0,
  runDelaySeconds: 0,
  diskWrite: 0,
  netSent: 0,
  threads: 5,
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
});
