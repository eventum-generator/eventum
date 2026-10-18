import { describe, expect, it } from 'vitest';

import {
  VARIANT_STYLE,
  instanceStatusLeaf,
  scenarioStatusBucket,
  statusVariant,
} from './statusPalette';
import { GeneratorStatus } from '@/api/routes/generators/schemas';
import { theme } from '@/theme';

const status = (overrides: Partial<GeneratorStatus>): GeneratorStatus => ({
  is_initializing: false,
  is_running: false,
  is_stopping: false,
  is_abandoned: false,
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
    ['a stuck instance', { is_running: true, is_abandoned: true }, 'stuck'],
    [
      'a stuck instance that was starting',
      { is_initializing: true, is_abandoned: true },
      'stuck',
    ],
  ])('reads %s as %s', (_, flags, variant) => {
    expect(statusVariant(status(flags))).toBe(variant);
  });
});

describe('a stuck instance', () => {
  const stuck = status({ is_running: true, is_abandoned: true });

  it('takes a leaf of its own rather than counting as active', () => {
    expect(instanceStatusLeaf(stuck)).toBe('stuck');
  });

  it('takes a scenario bucket of its own rather than running', () => {
    expect(scenarioStatusBucket(stuck)).toBe('stuck');
  });

  it('carries the danger palette', () => {
    expect(VARIANT_STYLE.stuck.bg).toBe('var(--mantine-color-red-light)');
    expect(VARIANT_STYLE.stuck.dot).toBe('var(--mantine-color-red-4)');
  });

  it('is told apart from a failed run by its indicator', () => {
    expect(VARIANT_STYLE.stuck.dot).not.toBe(VARIANT_STYLE.bad.dot);
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

  it.each(['good', 'warn', 'stuck'] as const)(
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
    expect(VARIANT_STYLE.done.dot).toBe('var(--mantine-color-green-8)');
    expect(VARIANT_STYLE.good.dot).toBe('var(--mantine-color-green-4)');
  });

  it('is deep enough to read as switched off', () => {
    // Both indicators come from one ramp, so hue cannot carry the difference -
    // brightness does.
    expect(luminance(shade('green', 8))).toBeLessThan(
      luminance(shade('green', 4)) * 0.5
    );
  });
});

describe('the halo', () => {
  it.each(['good', 'warn', 'stuck'] as const)(
    'lights the indicator of %s, the state of a live instance',
    (variant) => {
      expect(VARIANT_STYLE[variant].glow).toBeDefined();
    }
  );

  it.each(['done', 'bad', 'idle'] as const)(
    'leaves %s unlit, since the instance is not live',
    (variant) => {
      expect(VARIANT_STYLE[variant].glow).toBeUndefined();
    }
  );
});
