import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach } from 'vitest';

import { matchesMediaQuery, resetViewportWidth } from './viewport';

// Vitest runs without globals, so the automatic unmount React Testing
// Library installs on `afterEach` is not wired up - do it here.
afterEach(cleanup);
afterEach(resetViewportWidth);

const noop = () => {
  // The stubs below record nothing and report nothing.
};

// jsdom lays nothing out and implements none of the observers the app
// mounts with: Mantine reads `matchMedia`, and the editor observes both the
// size and the visibility of its element. The observers are inert - anything
// that depends on real geometry belongs in a browser test. Width queries do
// get answered, against a width the test sets, because a component that
// chooses its layout from one has no other way to be exercised. Changes are
// not broadcast: the width is set before mounting, not while mounted.
Object.defineProperty(globalThis, 'matchMedia', {
  writable: true,
  value: (query: string): MediaQueryList =>
    ({
      matches: matchesMediaQuery(query),
      media: query,
      onchange: null,
      addListener: noop,
      removeListener: noop,
      addEventListener: noop,
      removeEventListener: noop,
      dispatchEvent: () => false,
    }) as unknown as MediaQueryList,
});

// jsdom resolves no `calc()` over a CSS variable, which is how Mantine
// writes every size, so reading the computed style of a component throws
// instead of answering. Everything that measures an element runs into it,
// and the positioner behind a dropdown does so after the test that opened
// it has finished, where a throw counts as an unhandled error and fails
// the run. Such a read is answered with the style of an element outside
// the document instead - the empty values measuring code already handles.
const resolveStyle = globalThis.getComputedStyle.bind(globalThis);
const unstyledElement = document.createElement('div');

globalThis.getComputedStyle = ((element: Element, pseudoElement?: string) => {
  try {
    return resolveStyle(element, pseudoElement);
  } catch {
    return resolveStyle(unstyledElement);
  }
}) as typeof globalThis.getComputedStyle;

class ResizeObserverStub implements ResizeObserver {
  observe = noop;
  unobserve = noop;
  disconnect = noop;
}

class IntersectionObserverStub implements IntersectionObserver {
  readonly root = null;
  readonly rootMargin = '';
  readonly thresholds: readonly number[] = [];

  observe = noop;
  unobserve = noop;
  disconnect = noop;
  takeRecords = (): IntersectionObserverEntry[] => [];
}

globalThis.ResizeObserver = ResizeObserverStub;
globalThis.IntersectionObserver = IntersectionObserverStub;

// jsdom lays nothing out and so implements no scrolling. A dropdown
// scrolls the option it selects into view a tick after it opens, which
// lands after the test that opened it - an unhandled failure rather
// than a failed assertion.
Element.prototype.scrollIntoView = noop;

// The code editor measures the text it draws to place its cursor, and
// jsdom implements a Range without the geometry to answer with. The
// measurement runs a tick after a keystroke, so what it throws lands
// outside the test that typed - an unhandled failure rather than a
// failed assertion.
Range.prototype.getClientRects = function getClientRects() {
  return Object.assign([], { item: () => null }) as unknown as DOMRectList;
};
Range.prototype.getBoundingClientRect = () =>
  ({
    x: 0,
    y: 0,
    width: 0,
    height: 0,
    top: 0,
    right: 0,
    bottom: 0,
    left: 0,
    toJSON: () => ({}),
  }) as DOMRect;
