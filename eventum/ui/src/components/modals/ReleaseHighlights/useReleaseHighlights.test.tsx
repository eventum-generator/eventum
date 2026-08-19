import { renderHook } from '@testing-library/react';
import { FC, StrictMode } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { SEEN_VERSION_KEY, useReleaseHighlights } from './useReleaseHighlights';
import { useInstanceInfo } from '@/api/hooks/useInstance';
import { Release } from '@/releases';

vi.mock('@/api/hooks/useInstance', () => ({
  useInstanceInfo: vi.fn(),
}));

const Scene: FC = () => <svg />;

const RELEASES: Release[] = [
  {
    version: '2.8.0',
    changelogHref: 'https://example.test/2.8.0',
    highlights: [{ id: 'first', title: 'First', body: 'Body', scene: Scene }],
  },
];

function runningVersion(version?: string): void {
  vi.mocked(useInstanceInfo).mockReturnValue({
    data: version === undefined ? undefined : { app_version: version },
  } as unknown as ReturnType<typeof useInstanceInfo>);
}

/** Mounted the way the app mounts it - under StrictMode, whose double
 *  effect must not consume the decision the first pass made. */
function mountHook() {
  return renderHook(() => useReleaseHighlights(RELEASES), {
    wrapper: StrictMode,
  });
}

describe('useReleaseHighlights', () => {
  beforeEach(() => {
    globalThis.localStorage.clear();
    vi.clearAllMocks();
  });

  it('records the running version and stays closed on a fresh browser', () => {
    runningVersion('2.8.0');

    const { result } = mountHook();

    expect(result.current.opened).toBe(false);
    expect(globalThis.localStorage.getItem(SEEN_VERSION_KEY)).toBe('2.8.0');
  });

  it('opens when the version has changed since the last visit', () => {
    globalThis.localStorage.setItem(SEEN_VERSION_KEY, '2.7.0');
    runningVersion('2.8.0');

    const { result } = mountHook();

    expect(result.current.opened).toBe(true);
    expect(result.current.release?.version).toBe('2.8.0');
    expect(globalThis.localStorage.getItem(SEEN_VERSION_KEY)).toBe('2.8.0');
  });

  it('stays closed when the running version was already seen', () => {
    globalThis.localStorage.setItem(SEEN_VERSION_KEY, '2.8.0');
    runningVersion('2.8.0');

    expect(mountHook().result.current.opened).toBe(false);
  });

  it('does not open again on the next load', () => {
    globalThis.localStorage.setItem(SEEN_VERSION_KEY, '2.7.0');
    runningVersion('2.8.0');

    const first = mountHook();
    expect(first.result.current.opened).toBe(true);
    first.unmount();

    expect(mountHook().result.current.opened).toBe(false);
  });

  it('does not repeat a release when a patch carries no panels', () => {
    globalThis.localStorage.setItem(SEEN_VERSION_KEY, '2.8.0');
    runningVersion('2.8.1');

    const { result } = mountHook();

    expect(result.current.release?.version).toBe('2.8.0');
    expect(result.current.opened).toBe(false);
  });

  it('announces a release reached through a patch it has no panels for', () => {
    globalThis.localStorage.setItem(SEEN_VERSION_KEY, '2.7.0');
    runningVersion('2.8.1');

    expect(mountHook().result.current.opened).toBe(true);
  });

  it('stays closed when the browser cannot keep the version', () => {
    globalThis.localStorage.setItem(SEEN_VERSION_KEY, '2.7.0');
    runningVersion('2.8.0');

    const setItem = vi
      .spyOn(Storage.prototype, 'setItem')
      .mockImplementation(() => {
        throw new Error('storage is full');
      });

    // Panels that cannot be dismissed for good would open on every load.
    expect(mountHook().result.current.opened).toBe(false);

    setItem.mockRestore();
  });

  it('stays closed when the running version has no panels', () => {
    globalThis.localStorage.setItem(SEEN_VERSION_KEY, '1.9.0');
    runningVersion('2.0.0');

    const { result } = mountHook();

    expect(result.current.opened).toBe(false);
    expect(result.current.release).toBeUndefined();
    expect(globalThis.localStorage.getItem(SEEN_VERSION_KEY)).toBe('2.0.0');
  });

  it('decides once, not again when the instance reports a new version', () => {
    globalThis.localStorage.setItem(SEEN_VERSION_KEY, '2.8.0');
    runningVersion('2.8.0');

    const { result, rerender } = mountHook();
    expect(result.current.opened).toBe(false);

    // An instance upgraded under an open tab keeps serving the bundle of
    // the version it started on, so its panels are not this build's.
    runningVersion('2.9.0');
    rerender();

    expect(result.current.opened).toBe(false);
  });

  it('decides nothing until the running version is known', () => {
    globalThis.localStorage.setItem(SEEN_VERSION_KEY, '2.7.0');
    runningVersion();

    const { result } = mountHook();

    expect(result.current.opened).toBe(false);
    expect(globalThis.localStorage.getItem(SEEN_VERSION_KEY)).toBe('2.7.0');
  });
});
