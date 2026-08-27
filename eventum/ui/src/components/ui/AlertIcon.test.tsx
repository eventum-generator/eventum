import { render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { AlertIcon, AlertIconVariant } from './AlertIcon';

const VARIANTS: AlertIconVariant[] = ['error', 'info', 'success', 'warn'];

function iconOf(variant: AlertIconVariant, size?: number) {
  const { container } = render(<AlertIcon variant={variant} size={size} />);
  const svg = container.querySelector('svg');

  if (svg === null) {
    throw new Error('the alert icon drew nothing');
  }

  return svg;
}

/**
 * Every alert in the app takes its icon from here rather than picking a
 * glyph and a colour per call site. The point is that one variant reads
 * the same everywhere, so each has to be distinct from the others.
 */
describe('AlertIcon', () => {
  it.each(VARIANTS)('draws an icon for the %s variant', (variant) => {
    expect(iconOf(variant)).toBeInTheDocument();
  });

  it('gives every variant a colour of its own', () => {
    const colors = VARIANTS.map((variant) =>
      iconOf(variant).getAttribute('stroke')
    );

    expect(new Set(colors).size).toBe(VARIANTS.length);
    for (const color of colors) {
      expect(color).toMatch(/^var\(--mantine-color-/);
    }
  });

  it('gives every variant a glyph of its own', () => {
    const glyphs = VARIANTS.map((variant) =>
      iconOf(variant).getAttribute('class')
    );

    expect(new Set(glyphs).size).toBe(VARIANTS.length);
  });

  it('leaves the size to the icon unless one is given', () => {
    expect(iconOf('info').getAttribute('width')).not.toBe('40');
    expect(iconOf('info', 40).getAttribute('width')).toBe('40');
  });
});
