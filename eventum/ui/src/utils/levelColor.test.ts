import { describe, expect, it } from 'vitest';

import {
  CPU_THRESHOLDS,
  FD_THRESHOLDS,
  MEMORY_THRESHOLDS,
  QUEUE_THRESHOLDS,
  levelColor,
} from './levelColor';

const GREEN = 'var(--mantine-color-green-text)';
const YELLOW = 'var(--mantine-color-yellow-text)';
const RED = 'var(--mantine-color-red-text)';

/**
 * Every load readout in the app colours its figure through this, so the
 * same percentage has to read the same way wherever it appears. The
 * boundaries are what matters: a threshold that is exclusive on one
 * screen and inclusive on another is exactly the inconsistency this
 * function exists to prevent.
 */
describe('levelColor', () => {
  it.each([
    [0, GREEN],
    [59, GREEN],
    [60, YELLOW],
    [84, YELLOW],
    [85, RED],
    [100, RED],
  ])('colours %i%% against the cpu thresholds as %s', (pct, expected) => {
    expect(levelColor(pct, CPU_THRESHOLDS.warn, CPU_THRESHOLDS.bad)).toBe(
      expected
    );
  });

  it('treats a threshold as reached, not exceeded', () => {
    expect(levelColor(70, 70, 90)).toBe(YELLOW);
    expect(levelColor(90, 70, 90)).toBe(RED);
  });

  it('keeps a figure above the range red rather than wrapping around', () => {
    expect(levelColor(1000, 60, 85)).toBe(RED);
  });

  it('reads a negative figure as no load', () => {
    expect(levelColor(-1, 60, 85)).toBe(GREEN);
  });
});

describe('thresholds', () => {
  it.each([
    ['cpu', CPU_THRESHOLDS],
    ['memory', MEMORY_THRESHOLDS],
    ['descriptors', FD_THRESHOLDS],
    ['queue', QUEUE_THRESHOLDS],
  ])('orders the %s thresholds from warn to bad', (_name, thresholds) => {
    expect(thresholds.warn).toBeLessThan(thresholds.bad);
    expect(thresholds.warn).toBeGreaterThan(0);
    expect(thresholds.bad).toBeLessThanOrEqual(100);
  });

  it('warns earlier on descriptors than on cpu', () => {
    expect(FD_THRESHOLDS.warn).toBeLessThan(CPU_THRESHOLDS.warn);
  });

  it('reads a queue as full only at its limit', () => {
    expect(QUEUE_THRESHOLDS.bad).toBe(100);
  });
});
