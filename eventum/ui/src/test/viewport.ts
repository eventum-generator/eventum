/**
 * Viewport width the `matchMedia` stub answers width queries against.
 *
 * jsdom lays nothing out and implements no media queries, so a component
 * that picks its layout from one sees whatever this module reports. Tests
 * that care about the layout set the width; the rest get a desktop viewport.
 */

const DEFAULT_WIDTH = 1440;
const ROOT_FONT_SIZE = 16;

let width = DEFAULT_WIDTH;

/** Width in CSS pixels reported to width media queries. */
export function setViewportWidth(value: number): void {
  width = value;
}

/** Restore the default desktop width. */
export function resetViewportWidth(): void {
  width = DEFAULT_WIDTH;
}

/**
 * Evaluate the width features of a media query against the current width.
 *
 * Only `min-width` and `max-width` in `px` or `em` are understood - the
 * features layout decisions are actually made on. A query carrying none of
 * them does not match, so an unsupported feature reads as "off" rather than
 * as an accidental match.
 */
export function matchesMediaQuery(query: string): boolean {
  const features = [
    ...query.matchAll(/\((min|max)-width:\s*([\d.]+)(px|em|rem)\)/g),
  ];

  if (features.length === 0) {
    return false;
  }

  return features.every(([, bound, value, unit]) => {
    const pixels =
      unit === 'px' ? Number(value) : Number(value) * ROOT_FONT_SIZE;

    return bound === 'min' ? width >= pixels : width <= pixels;
  });
}
