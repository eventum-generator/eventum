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

describe('the status chip', () => {
  it.each(['done', 'bad', 'idle'] as const)(
    'keeps %s on the neutral chip, since the instance is not live',
    (variant) => {
      // A colored chip of any shade reads as a live one once diluted to a
      // tint, and in a table the two sit rows apart with nothing to compare
      // against.
      expect(VARIANT_STYLE[variant].bg).toBe(VARIANT_STYLE.idle.bg);
      expect(VARIANT_STYLE[variant].fg).toBe(VARIANT_STYLE.idle.fg);
    }
  );

  it.each(['good', 'warn'] as const)(
    'colors the chip of %s, the state of a live instance',
    (variant) => {
      expect(VARIANT_STYLE[variant].bg).not.toBe(VARIANT_STYLE.idle.bg);
    }
  );

  it('tells the states at rest apart by their indicator alone', () => {
    const atRest = [
      VARIANT_STYLE.done.dot,
      VARIANT_STYLE.bad.dot,
      VARIANT_STYLE.idle.dot,
    ];

    expect(new Set(atRest).size).toBe(atRest.length);
  });
});

describe('the finished indicator', () => {
  it('takes the running green, deep instead of vivid', () => {
    expect(VARIANT_STYLE.done.dot).toBe('var(--mantine-color-green-6)');
    expect(VARIANT_STYLE.good.dot).toBe('var(--mantine-color-green-4)');
  });

  it('is deep enough to read as switched off', () => {
    // Both indicators come from one ramp, so hue cannot carry the difference -
    // brightness does.
    expect(luminance(shade('green', 6))).toBeLessThan(
      luminance(shade('green', 4)) * 0.5
    );
  });
});
