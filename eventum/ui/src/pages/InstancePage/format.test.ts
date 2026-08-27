import { describe, expect, it } from 'vitest';

import {
  formatCompact,
  formatEps,
  formatSeconds,
  formatUptime,
} from './format';

/**
 * These labels sit in a monospace strip whose width is fixed, so the
 * point of each is how much precision it keeps: a rate below ten still
 * has to read as a rate rather than as zero, while one in the thousands
 * has no room for decimals.
 */
describe('formatEps', () => {
  it.each([
    [0, '0.00'],
    [0.04, '0.04'],
    [9.99, '9.99'],
    [10, '10.0'],
    [99.94, '99.9'],
    [100, '100'],
    [1234.6, '1,235'],
  ])('reads %s as %s', (value, expected) => {
    expect(formatEps(value)).toBe(expected);
  });

  it('keeps a rate too small for one decimal visible', () => {
    expect(formatEps(0.004)).not.toBe('0');
  });
});

describe('formatCompact', () => {
  it.each([
    [0, '0'],
    [999, '999'],
    [1000, '1K'],
    [12_400, '12.4K'],
    [1_000_000, '1M'],
  ])('reads %i as %s', (value, expected) => {
    expect(formatCompact(value)).toBe(expected);
  });
});

/**
 * A duration below a minute is read as a measurement, so it keeps its
 * fraction; above one it is read as elapsed time, where the fraction is
 * noise.
 */
describe('formatSeconds', () => {
  it.each([
    [0, '0.00s'],
    [0.25, '0.25s'],
    [59.994, '59.99s'],
  ])('reads %s seconds as %s', (value, expected) => {
    expect(formatSeconds(value)).toBe(expected);
  });

  it('drops the fraction once past a minute', () => {
    expect(formatSeconds(65)).toBe('1m 05s');
  });

  it('reads a negative duration as none', () => {
    expect(formatSeconds(-5)).toBe('0.00s');
  });
});

describe('formatUptime', () => {
  it.each([
    [0, '0s'],
    [45, '45s'],
    [60, '1m 00s'],
    [125, '2m 05s'],
    [3600, '1h 0m'],
    [3660, '1h 1m'],
    [86_400, '1d 0h'],
    [90_000, '1d 1h'],
  ])('reads %i seconds as %s', (value, expected) => {
    expect(formatUptime(value)).toBe(expected);
  });

  it('pads the seconds of a sub-hour uptime, keeping the width stable', () => {
    expect(formatUptime(61)).toBe('1m 01s');
  });

  it('reads a negative uptime as none', () => {
    expect(formatUptime(-1)).toBe('0s');
  });
});
