import { describe, expect, it } from 'vitest';

import { nextSelectedIndex } from './selection';

describe('nextSelectedIndex', () => {
  it('follows the selected plugin when an earlier one is removed', () => {
    // [A, B, C] with B selected, A removed -> [B, C] with B selected.
    expect(nextSelectedIndex(1, 0, 2)).toBe(0);
    expect(nextSelectedIndex(3, 1, 3)).toBe(2);
  });

  it('keeps the position when the selected plugin is removed', () => {
    // [A, B, C] with B selected, B removed -> [A, C] with C selected.
    expect(nextSelectedIndex(1, 1, 2)).toBe(1);
  });

  it('clamps to the last plugin when the selected one was last', () => {
    // [A, B] with B selected, B removed -> [A] with A selected.
    expect(nextSelectedIndex(1, 1, 1)).toBe(0);
  });

  it('keeps the selection when a later plugin is removed', () => {
    // [A, B, C] with A selected, C removed -> [A, B] with A selected.
    expect(nextSelectedIndex(0, 2, 2)).toBe(0);
  });

  it('falls back to zero when the list is emptied', () => {
    expect(nextSelectedIndex(0, 0, 0)).toBe(0);
  });
});
