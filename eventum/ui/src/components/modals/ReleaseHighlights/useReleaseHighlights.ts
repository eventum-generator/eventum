import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { useInstanceInfo } from '@/api/hooks/useInstance';
import { RELEASES, Release, pickRelease } from '@/releases';
import { compareVersions } from '@/utils/version';

/** Where a browser keeps the version whose panels it was already shown. */
export const SEEN_VERSION_KEY = 'release-highlights-seen';

function readSeenVersion(): string | null {
  try {
    return globalThis.localStorage.getItem(SEEN_VERSION_KEY);
  } catch {
    // A browser that keeps nothing is treated as one that has seen
    // everything: the panels cannot be dismissed for good there, and
    // showing them on every load is worse than not showing them.
    return null;
  }
}

/** Report whether the version could be kept. */
function keepSeenVersion(version: string): boolean {
  try {
    globalThis.localStorage.setItem(SEEN_VERSION_KEY, version);

    return true;
  } catch {
    return false;
  }
}

export interface ReleaseHighlightsState {
  /** The release this instance has panels for, if there is one. */
  release: Release | undefined;
  opened: boolean;
  open: () => void;
  close: () => void;
}

/**
 * The release panels of the running instance, opened once per upgrade.
 *
 * The decision is made once, as soon as the running version is known:
 * the version the browser was last shown is read, the running one is
 * written in its place, and the panels open only when the browser has
 * not reached the release they describe yet. That is the release, not
 * the running version: a patch shows the panels of the release it
 * follows, and a browser already shown them is not shown them again. A
 * browser that stored nothing has just met this instance - it is
 * recorded silently, so a new user is not greeted with a summary of
 * changes they never lived through.
 *
 * The version is recorded at that moment rather than when the panels are
 * closed, so a reload half way through does not bring them back. A
 * browser that cannot keep it is left alone for the same reason: panels
 * that cannot be dismissed for good are worse than no panels.
 */
export function useReleaseHighlights(
  releases: Release[] = RELEASES
): ReleaseHighlightsState {
  const { data: instanceInfo } = useInstanceInfo();
  const appVersion = instanceInfo?.app_version;

  const [opened, setOpened] = useState(false);
  const isDecided = useRef(false);

  const release = useMemo(
    () =>
      appVersion === undefined ? undefined : pickRelease(appVersion, releases),
    [appVersion, releases]
  );

  useEffect(() => {
    if (appVersion === undefined || isDecided.current) {
      return;
    }

    isDecided.current = true;

    const seenVersion = readSeenVersion();

    if (!keepSeenVersion(appVersion) || seenVersion === null) {
      return;
    }

    if (release === undefined) {
      return;
    }

    if (compareVersions(seenVersion, release.version) >= 0) {
      return;
    }

    setOpened(true);
  }, [appVersion, release]);

  const open = useCallback(() => setOpened(true), []);
  const close = useCallback(() => setOpened(false), []);

  return { release, opened, open, close };
}
