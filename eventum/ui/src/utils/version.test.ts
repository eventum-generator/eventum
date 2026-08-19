import { describe, expect, it } from 'vitest';

import { compareVersions } from './version';

describe('compareVersions', () => {
  it('orders by the first differing segment', () => {
    expect(compareVersions('2.7.0', '2.8.0')).toBeLessThan(0);
    expect(compareVersions('2.8.1', '2.8.0')).toBeGreaterThan(0);
    expect(compareVersions('3.0.0', '2.99.99')).toBeGreaterThan(0);
  });

  it('treats equal versions as equal', () => {
    expect(compareVersions('2.8.0', '2.8.0')).toBe(0);
  });

  it('counts a missing segment as zero', () => {
    expect(compareVersions('2.8', '2.8.0')).toBe(0);
    expect(compareVersions('2.8', '2.8.1')).toBeLessThan(0);
  });

  it('orders a version on its way to a number before that number', () => {
    expect(compareVersions('2.8.0rc1', '2.8.0')).toBeLessThan(0);
    expect(compareVersions('2.8.0', '2.8.0rc1')).toBeGreaterThan(0);
    expect(compareVersions('2.8.0rc1', '2.8.0rc2')).toBe(0);
    expect(compareVersions('2.8.0rc1', '2.9.0')).toBeLessThan(0);
    expect(compareVersions('2.8.0rc1', '2.7.0')).toBeGreaterThan(0);
  });

  it('counts an unparsable segment as zero instead of throwing', () => {
    expect(compareVersions('dev', '2.8.0')).toBeLessThan(0);
    expect(compareVersions('', '0.0.0')).toBe(0);
  });
});
