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
