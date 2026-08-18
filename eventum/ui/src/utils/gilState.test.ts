import { describe, expect, it } from 'vitest';

import { describeGilState } from './gilState';

describe('describeGilState', () => {
  it('reports a standard build neutrally', () => {
    const state = describeGilState({
      python_free_threaded: false,
      python_gil_enabled: true,
    });

    expect(state.value).toBe('Enabled');
    expect(state.warning).toBe(false);
    expect(state.color).toBeUndefined();
  });

  it('reports a free-threaded build with the GIL off as the intended setup', () => {
    const state = describeGilState({
      python_free_threaded: true,
      python_gil_enabled: false,
    });

    expect(state.value).toBe('Disabled');
    expect(state.warning).toBe(false);
    expect(state.color).toContain('green');
  });

  it('warns when the GIL came back on a free-threaded build', () => {
    const state = describeGilState({
      python_free_threaded: true,
      python_gil_enabled: true,
    });

    expect(state.value).toBe('Enabled');
    expect(state.warning).toBe(true);
    expect(state.color).toContain('yellow');
  });
});
