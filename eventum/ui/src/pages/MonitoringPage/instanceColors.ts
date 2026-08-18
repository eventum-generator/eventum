import { OTHER_BAND } from './history';

// Categorical palette for per-instance bands. Brand hues lead; the rest are
// distinct mid-saturation colours that stay legible on both themes. Semantic
// red is reserved for failures and deliberately omitted.
/* eslint-disable no-restricted-syntax -- categorical chart series needs distinct swatches beyond the token set */
const PALETTE = [
  'var(--mantine-color-primary-text)',
  'var(--mantine-color-cyan-text)',
  '#3fb950',
  '#d29922',
  '#4d9fff',
  '#c77dff',
  '#2dd4bf',
  '#fb923c',
];
/* eslint-enable no-restricted-syntax */

export const FALLBACK_COLOR = 'var(--mantine-color-primary-text)';

/** Colour of the band that folds everything past the top of the ranking. */
export const OTHER_COLOR = 'var(--mantine-color-dimmed)';

/**
 * Colour per instance id, stable across polls so a band and its table row
 * keep the same swatch while the ranking moves under them. Ids are taken in
 * alphabetical order rather than by rank for that reason.
 */
export function instanceColors(ids: string[]): Map<string, string> {
  const map = new Map<string, string>();
  let index = 0;

  for (const id of [...ids].sort((a, b) => a.localeCompare(b))) {
    if (id === OTHER_BAND) {
      map.set(id, OTHER_COLOR);
      continue;
    }
    map.set(id, PALETTE[index % PALETTE.length] ?? FALLBACK_COLOR);
    index++;
  }

  return map;
}
