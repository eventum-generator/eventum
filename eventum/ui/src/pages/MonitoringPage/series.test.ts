import { describe, expect, it } from 'vitest';

import {
  FlowPoint,
  MAX_POINTS,
  ResourcePoint,
  WINDOW_OPTIONS,
  dualRateData,
  errorData,
  fixedWindow,
  gaugePoints,
  instanceLoadData,
  throughputData,
} from './history';

function flow(t: number, values: Partial<FlowPoint> = {}): FlowPoint {
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

function resources(t: number, values: Partial<ResourcePoint> = {}) {
  return {
    t,
    cpu: 0,
    memPct: 0,
    diskRead: 0,
    diskWrite: 0,
    netRecv: 0,
    netSent: 0,
    ...values,
  } as ResourcePoint;
}

/**
 * Every counter the backend reports is cumulative, so a chart of what
 * is happening now is a chart of differences. Two things follow, and
 * both are here: a single sample says nothing yet, and a counter that
 * went backwards - a restarted instance - must not draw a negative
 * rate.
 */
describe('throughputData', () => {
  it('says nothing from a single sample', () => {
    expect(throughputData([flow(0, { generated: 10 })])).toEqual([]);
  });

  it('derives the rate from the growth between two samples', () => {
    const rows = throughputData([
      flow(0, { generated: 10, written: 5 }),
      flow(2000, { generated: 30, written: 15 }),
    ]);

    expect(rows).toHaveLength(1);
    expect(rows[0]?.input).toBe(10);
    expect(rows[0]?.output).toBe(5);
  });

  it('reads a counter that went backwards as no throughput', () => {
    const rows = throughputData([
      flow(0, { generated: 100 }),
      flow(1000, { generated: 10 }),
    ]);

    expect(rows[0]?.input).toBe(0);
  });

  it('reads two samples at the same moment as no throughput', () => {
    const rows = throughputData([
      flow(1000, { generated: 10 }),
      flow(1000, { generated: 20 }),
    ]);

    expect(rows[0]?.input).toBe(0);
  });

  it('yields one row fewer than the samples it was given', () => {
    const rows = throughputData([flow(0), flow(1000), flow(2000)]);

    expect(rows).toHaveLength(2);
  });

  it('stamps every row with the clock time of its later sample', () => {
    const rows = throughputData([flow(0), flow(60_000)]);

    expect(rows[0]?.t).toBe(60_000);
    expect(rows[0]?.time).toMatch(/^\d{2}:\d{2}:\d{2}$/);
  });
});

/**
 * Failures are split by the stage that produced them, so the chart says
 * whether the events or the writing is at fault.
 */
describe('errorData', () => {
  it('keeps the two stages apart', () => {
    const rows = errorData([
      flow(0),
      flow(1000, { produceFailed: 2, writeFailed: 3, formatFailed: 1 }),
    ]);

    expect(rows[0]?.event).toBe(2);
    expect(rows[0]?.output).toBe(4);
  });

  it('counts a write and a format failure as one output stage', () => {
    const rows = errorData([
      flow(0, { writeFailed: 1, formatFailed: 1 }),
      flow(1000, { writeFailed: 2, formatFailed: 3 }),
    ]);

    expect(rows[0]?.output).toBe(3);
  });
});

describe('gaugePoints', () => {
  it('reads a gauge straight through, one point per sample', () => {
    const points = gaugePoints(
      [resources(0, { cpu: 10 }), resources(1000, { cpu: 20 })],
      'cpu'
    );

    expect(points.map((point) => point.value)).toEqual([10, 20]);
  });

  it('says nothing when nothing was sampled', () => {
    expect(gaugePoints([], 'memPct')).toEqual([]);
  });
});

describe('dualRateData', () => {
  it('turns two cumulative counters into two rates', () => {
    const rows = dualRateData(
      [
        resources(0, { diskRead: 100, diskWrite: 50 }),
        resources(2000, { diskRead: 300, diskWrite: 150 }),
      ],
      'diskRead',
      'diskWrite'
    );

    expect(rows[0]?.in).toBe(100);
    expect(rows[0]?.out).toBe(50);
  });

  it('says nothing from a single sample', () => {
    expect(dualRateData([resources(0)], 'netRecv', 'netSent')).toEqual([]);
  });
});

/**
 * The chart keeps its width whatever it holds, so a short history is
 * padded on the left with empty slots rather than stretched across it.
 */
describe('fixedWindow', () => {
  interface Slot {
    t: number;
    time: string;
    value: number | null;
  }

  const empty = { value: null };

  it('pads a short series on the left', () => {
    const padded = fixedWindow<Slot>(
      [{ t: 10_000, time: '00:00:10', value: 1 }],
      4,
      empty
    );

    expect(padded).toHaveLength(4);
    expect(padded.slice(0, 3).every((point) => point.value === null)).toBe(
      true
    );
    expect(padded[3]?.value).toBe(1);
  });

  it('keeps a full series as it is', () => {
    const data: Slot[] = [
      { t: 0, time: '00:00:00', value: 1 },
      { t: 5000, time: '00:00:05', value: 2 },
    ];

    expect(fixedWindow<Slot>(data, 2, empty)).toEqual(data);
  });

  it('drops the oldest points once the series outgrows the window', () => {
    const data: Slot[] = [
      { t: 0, time: 'a', value: 1 },
      { t: 5000, time: 'b', value: 2 },
      { t: 10_000, time: 'c', value: 3 },
    ];

    expect(fixedWindow<Slot>(data, 2, empty).map((p) => p.value)).toEqual([
      2, 3,
    ]);
  });

  it('fills an empty series entirely with empty slots', () => {
    const padded = fixedWindow<Slot>([], 3, empty);

    expect(padded).toHaveLength(3);
    expect(padded.every((point) => point.value === null)).toBe(true);
  });

  it('spaces the padded slots one poll apart, before the first real one', () => {
    const padded = fixedWindow<Slot>(
      [{ t: 100_000, time: 'x', value: 1 }],
      3,
      empty
    );

    expect(padded[0]?.t).toBe(90_000);
    expect(padded[1]?.t).toBe(95_000);
  });
});

/**
 * Per-instance rates are summed into the fleet rate, so an instance
 * that has only just appeared has to contribute nothing rather than its
 * whole counter.
 */
describe('instanceLoadData', () => {
  it('derives a rate per instance', () => {
    const rows = instanceLoadData([
      { t: 0, time: '00:00:00', written: { web: 0, db: 10 } },
      { t: 2000, time: '00:00:02', written: { web: 20, db: 30 } },
    ]);

    expect(rows[0]?.rates).toEqual({ web: 10, db: 10 });
  });

  it('gives an instance new in this sample no rate yet', () => {
    const rows = instanceLoadData([
      { t: 0, time: '00:00:00', written: { web: 0 } },
      { t: 1000, time: '00:00:01', written: { web: 5, fresh: 1000 } },
    ]);

    expect(rows[0]?.rates.fresh).toBe(0);
    expect(rows[0]?.rates.web).toBe(5);
  });

  it('drops an instance that is gone from the later sample', () => {
    const rows = instanceLoadData([
      { t: 0, time: '00:00:00', written: { web: 0, gone: 5 } },
      { t: 1000, time: '00:00:01', written: { web: 5 } },
    ]);

    expect(Object.keys(rows[0]?.rates ?? {})).toEqual(['web']);
  });
});

describe('the chart windows', () => {
  it('offers the default window among the choices', () => {
    expect(WINDOW_OPTIONS.map((option) => option.value)).toContain(
      String(MAX_POINTS)
    );
  });

  it('offers them from shortest to longest', () => {
    const points = WINDOW_OPTIONS.map((option) => Number(option.value));

    expect(points).toEqual([...points].sort((a, b) => a - b));
  });
});
