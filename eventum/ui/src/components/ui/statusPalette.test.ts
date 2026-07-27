import { MantineTheme } from '@mantine/core';
import { describe, expect, it } from 'vitest';

import { VARIANT_STYLE, statusVariant } from './statusPalette';
import { GeneratorStatus } from '@/api/routes/generators/schemas';
import { cssVariablesResolver, theme } from '@/theme';

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

/* eslint-disable unicorn/numeric-separators-style -- the sRGB and CIELAB
   constants below are written the way they are published. */

/** CIELAB of a hex colour, via linear sRGB and XYZ (D65). */
function lab(hex: string): [number, number, number] {
  const [r, g, b] = [1, 3, 5].map((i) => {
    const srgb = Number.parseInt(hex.slice(i, i + 2), 16) / 255;
    return srgb <= 0.04045 ? srgb / 12.92 : ((srgb + 0.055) / 1.055) ** 2.4;
  }) as [number, number, number];

  const [x, y, z] = [
    (0.4124564 * r + 0.3575761 * g + 0.1804375 * b) / 0.95047,
    0.2126729 * r + 0.7151522 * g + 0.072175 * b,
    (0.0193339 * r + 0.119192 * g + 0.9503041 * b) / 1.08883,
  ].map((v) => (v > 0.008856 ? v ** (1 / 3) : 7.787 * v + 16 / 116)) as [
    number,
    number,
    number,
  ];

  return [116 * y - 16, 500 * (x - y), 200 * (y - z)];
}

/* eslint-enable unicorn/numeric-separators-style */

/** How colourful a colour is - the "is the indicator lit" axis. */
function chroma(hex: string): number {
  const [, a, b] = lab(hex);
  return Math.hypot(a, b);
}

/** Hue angle in degrees - which colour family a shade belongs to. */
function hue(hex: string): number {
  const [, a, b] = lab(hex);
  return ((Math.atan2(b, a) * 180) / Math.PI + 360) % 360;
}

/** Shortest angle between two hues, so the 0/360 seam does not inflate it. */
function hueDistance(one: string, other: string): number {
  const distance = Math.abs(hue(one) - hue(other)) % 360;
  return Math.min(distance, 360 - distance);
}

// Shade 6 carries a role's light-scheme colour and shade 4 its dark-scheme
// one, so these two are the shades a status indicator draws from.
const RENDERED_SHADES = [4, 6];

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

describe('the finished status colour', () => {
  it('renders the settled shade of its ramp where a running one is lit', () => {
    expect(VARIANT_STYLE.done.dot).toBe(
      'var(--mantine-color-sage-light-color)'
    );
    expect(VARIANT_STYLE.good.dot).toBe('var(--mantine-color-green-4)');
  });

  it('stays on the settled shade in the dark scheme as well', () => {
    const { dark } = cssVariablesResolver({} as MantineTheme);

    // Every other semantic role jumps to the vivid end of its ramp in the
    // dark scheme. Terminal success must not: that is the lit look.
    expect(dark?.['--mantine-color-sage-light-color']).toBe(
      'var(--mantine-color-sage-6)'
    );
    expect(dark?.['--mantine-color-green-light-color']).toBe(
      'var(--mantine-color-green-4)'
    );
  });

  it.each(RENDERED_SHADES)(
    'stays in the running green hue family at shade %i',
    (index) => {
      expect(
        hueDistance(shade('sage', index), shade('green', index))
      ).toBeLessThan(15);
    }
  );

  it.each(RENDERED_SHADES)(
    'drops most of the running green chroma at shade %i',
    (index) => {
      // A finished instance reads as an unlit indicator on its own, with no
      // running one next to it to compare against. Splitting the two by hue
      // instead - a teal against a green - did not carry that at a glance.
      expect(chroma(shade('sage', index))).toBeLessThan(
        chroma(shade('green', index)) * 0.55
      );
    }
  );
});
