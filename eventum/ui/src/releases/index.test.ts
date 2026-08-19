import { readFileSync } from 'node:fs';
import path from 'node:path';
import { FC } from 'react';
import { describe, expect, it } from 'vitest';

import { RELEASES, Release, pickRelease } from './index';
import { compareVersions } from '@/utils/version';

const Scene: FC = () => null;

const PANEL = { id: 'panel', title: 'Panel', body: 'Body', scene: Scene };

const RELEASE_A: Release = {
  version: '2.6.0',
  changelogHref: 'https://example.test/2.6.0',
  highlights: [PANEL],
};

const RELEASE_B: Release = {
  version: '2.8.0',
  changelogHref: 'https://example.test/2.8.0',
  highlights: [PANEL],
};

describe('pickRelease', () => {
  it('picks the release the running version is', () => {
    expect(pickRelease('2.8.0', [RELEASE_A, RELEASE_B])).toBe(RELEASE_B);
  });

  it('keeps the previous release on a patch that carries no panels', () => {
    expect(pickRelease('2.8.3', [RELEASE_A, RELEASE_B])).toBe(RELEASE_B);
  });

  it('never picks a release the running version has not reached', () => {
    expect(pickRelease('2.7.9', [RELEASE_A, RELEASE_B])).toBe(RELEASE_A);
    expect(pickRelease('2.0.0', [RELEASE_A, RELEASE_B])).toBeUndefined();
  });

  it('reports nothing when no release is described', () => {
    expect(pickRelease('2.8.0', [])).toBeUndefined();
  });

  it('passes over a release that describes nothing', () => {
    const empty: Release = { ...RELEASE_B, highlights: [] };

    expect(pickRelease('2.8.0', [RELEASE_A, empty])).toBe(RELEASE_A);
  });
});

/** The version the package ships as, which the panels run ahead of. */
function packageVersion(): string {
  // Tests run from `eventum/ui`, beside the package they belong to.
  const source = readFileSync(
    path.resolve(process.cwd(), '../__init__.py'),
    'utf8'
  );
  const match = /__version__ = '([^']+)'/.exec(source);

  expect(match).not.toBeNull();

  return match![1]!;
}

describe('RELEASES', () => {
  // Panels are written during the cycle, so the newest entry names the
  // version being prepared - never a version already left behind, which
  // is what a release that forgot its panels looks like.
  it('reaches the version the package ships as', () => {
    expect(RELEASES.length).toBeGreaterThan(0);
    expect(
      compareVersions(RELEASES[0]!.version, packageVersion())
    ).toBeGreaterThanOrEqual(0);
  });

  it('lists the releases newest first', () => {
    const versions = RELEASES.map((release) => release.version);

    expect(new Set(versions).size).toBe(versions.length);
    const newestFirst = [...versions].sort((left, right) =>
      compareVersions(right, left)
    );

    expect(newestFirst).toEqual(versions);
  });

  it('describes every panel it ships', () => {
    for (const release of RELEASES) {
      expect(release.highlights.length).toBeGreaterThan(0);

      const ids = release.highlights.map((panel) => panel.id);
      expect(new Set(ids).size).toBe(ids.length);

      for (const panel of release.highlights) {
        expect(panel.title).not.toBe('');
        expect(panel.body).not.toBe('');
      }
    }
  });
});
