import { describe, expect, it } from 'vitest';

import { PANEL_MIN_WIDTH, panelStyle, resolvePanel } from './layout';

describe('resolvePanel', () => {
  it('keeps the selected panel when it is available', () => {
    expect(resolvePanel('inspector', true)).toBe('inspector');
    expect(resolvePanel('explorer', true)).toBe('explorer');
    expect(resolvePanel('explorer', false)).toBe('explorer');
  });

  it('falls back to the editor when the inspector is gone', () => {
    expect(resolvePanel('inspector', false)).toBe('editor');
  });
});

describe('panelStyle on a shared row', () => {
  const shared = { active: null };

  it('holds the editor at a width code can be read at', () => {
    expect(panelStyle('editor', shared)).toEqual({
      minWidth: PANEL_MIN_WIDTH.editor,
    });
  });

  it('lets the docks give way down to their handle limits', () => {
    expect(panelStyle('explorer', { ...shared, size: 248 })).toEqual({
      width: 248,
      flex: '0 1 auto',
      minWidth: PANEL_MIN_WIDTH.explorer,
    });
    expect(panelStyle('inspector', { ...shared, size: 360 })).toEqual({
      width: 360,
      flex: '0 1 auto',
      minWidth: PANEL_MIN_WIDTH.inspector,
    });
  });
});

describe('panelStyle with one panel at a time', () => {
  it('gives the row to the active panel', () => {
    expect(panelStyle('explorer', { active: 'explorer' })).toEqual({
      flex: '1 1 auto',
    });
  });

  it('hides the rest instead of dropping them', () => {
    expect(panelStyle('editor', { active: 'explorer' })).toEqual({
      display: 'none',
    });
    expect(panelStyle('inspector', { active: 'explorer' })).toEqual({
      display: 'none',
    });
  });

  it('ignores the handle width the docks no longer have', () => {
    expect(panelStyle('explorer', { active: 'editor', size: 248 })).toEqual({
      display: 'none',
    });
  });
});
