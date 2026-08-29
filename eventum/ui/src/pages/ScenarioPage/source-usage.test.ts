import { describe, expect, it } from 'vitest';

import { buildSourceUsage } from './source-usage';

describe('buildSourceUsage', () => {
  it('groups templates and scripts by file path', () => {
    const entries = buildSourceUsage({
      writes: [
        { key: 'pool', path: 'scripts/produce.py' },
        { key: 'counter', path: 'templates/event.jinja' },
      ],
      reads: [{ key: 'pool', path: 'templates/event.jinja' }],
      warnings: [],
    });

    expect(entries.map((entry) => entry.path)).toEqual([
      'scripts/produce.py',
      'templates/event.jinja',
    ]);
    expect(entries[0]).toEqual({
      path: 'scripts/produce.py',
      writes: ['pool'],
      reads: [],
      warnings: [],
    });
    expect(entries[1]?.reads).toEqual(['pool']);
  });

  it('deduplicates repeated keys of one file', () => {
    const entries = buildSourceUsage({
      writes: [
        { key: 'pool', path: 'produce.py' },
        { key: 'pool', path: 'produce.py' },
      ],
      reads: [],
      warnings: [],
    });

    expect(entries[0]?.writes).toEqual(['pool']);
  });

  it('keeps a file that only produced a warning', () => {
    const entries = buildSourceUsage({
      writes: [],
      reads: [],
      warnings: [{ type: 'dynamic_key', path: 'produce.py' }],
    });

    expect(entries).toEqual([
      { path: 'produce.py', writes: [], reads: [], warnings: ['dynamic_key'] },
    ]);
  });

  it('returns nothing without usage', () => {
    expect(buildSourceUsage()).toEqual([]);
  });
});
