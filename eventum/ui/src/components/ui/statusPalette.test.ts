import { describe, expect, it } from 'vitest';

import { VARIANT_STYLE, statusVariant } from './statusPalette';
import { GeneratorStatus } from '@/api/routes/generators/schemas';
import { theme } from '@/theme';

const status = (overrides: Partial<GeneratorStatus>): GeneratorStatus => ({
  is_initializing: false,
  is_running: false,
  is_stopping: false,
  is_ended_up: false,
  is_ended_up_successfully: false,
  ...overrides,
});

/** One shade of a theme ramp. */
function shade(color: string, index: number): string {
  const value = theme.colors?.[color]?.[index];
  if (value === undefined) {
    throw new Error(`the theme has no ${color} ramp`);
  }
  return value;
}

/* eslint-disable unicorn/numeric-separators-style -- the sRGB constants below
   are written the way they are published. */

/** Relative luminance of a hex colour - how brightly it reads. */
function luminance(hex: string): number {
  const [r, g, b] = [1, 3, 5].map((i) => {
    const srgb = Number.parseInt(hex.slice(i, i + 2), 16) / 255;
    return srgb <= 0.04045 ? srgb / 12.92 : ((srgb + 0.055) / 1.055) ** 2.4;
  }) as [number, number, number];

  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

/* eslint-enable unicorn/numeric-separators-style */

describe('statusVariant', () => {
  it.each([
    ['a running instance', { is_running: true }, 'good'],
    ['a starting instance', { is_initializing: true }, 'warn'],
    ['a stopping instance', { is_stopping: true }, 'warn'],
    [
      'an instance that finished',
      { is_ended_up: true, is_ended_up_successfully: true },
      'done',
    ],
    ['an instance that failed', { is_ended_up: true }, 'bad'],
    ['an instance that never ran', {}, 'idle'],
  ])('reads %s as %s', (_, flags, variant) => {
    expect(statusVariant(status(flags))).toBe(variant);
  });
});

describe('the finished status', () => {
  it('takes the neutral chip of a state at rest, not a green one', () => {
    // A green chip of any shade reads as a running instance once diluted to a
    // tint, and in a table the two sit rows apart with nothing to compare
    // against.
    expect(VARIANT_STYLE.done.bg).toBe(VARIANT_STYLE.idle.bg);
    expect(VARIANT_STYLE.done.fg).toBe(VARIANT_STYLE.idle.fg);
    expect(VARIANT_STYLE.done.bg).not.toBe(VARIANT_STYLE.good.bg);
  });

  it('keeps its green in the indicator alone', () => {
    expect(VARIANT_STYLE.done.dot).toBe('var(--mantine-color-green-6)');
    expect(VARIANT_STYLE.good.dot).toBe('var(--mantine-color-green-4)');
    expect(VARIANT_STYLE.done.dot).not.toBe(VARIANT_STYLE.idle.dot);
  });

  it('draws that indicator deep enough to read as switched off', () => {
    // Both indicators come from one ramp, so hue cannot carry the difference -
    // brightness does.
    expect(luminance(shade('green', 6))).toBeLessThan(
      luminance(shade('green', 4)) * 0.5
    );
  });
});
