import { describe, expect, it } from 'vitest';

import { buildEntryUrl } from './entry-url';

describe('buildEntryUrl', () => {
  it('links a GitHub repository at the named branch', () => {
    expect(
      buildEntryUrl(
        'https://github.com/eventum-generator/content-packs.git',
        'develop',
        'generators/web-nginx'
      )
    ).toBe(
      'https://github.com/eventum-generator/content-packs/tree/develop/generators/web-nginx'
    );
  });

  it('falls back to the default branch when none is named', () => {
    expect(
      buildEntryUrl(
        'https://github.com/eventum-generator/content-packs',
        null,
        'generators/web-nginx'
      )
    ).toBe(
      'https://github.com/eventum-generator/content-packs/tree/HEAD/generators/web-nginx'
    );
  });

  it('uses the GitLab layout', () => {
    expect(
      buildEntryUrl('https://gitlab.com/team/packs.git', 'main', 'generators/a')
    ).toBe('https://gitlab.com/team/packs/-/tree/main/generators/a');
  });

  it('keeps the separators of a branch name that holds slashes', () => {
    expect(
      buildEntryUrl(
        'https://github.com/team/packs.git',
        'release/1.0',
        'generators/a'
      )
    ).toBe('https://github.com/team/packs/tree/release/1.0/generators/a');
  });

  it('uses the GitLab layout for a self-hosted GitLab', () => {
    expect(
      buildEntryUrl('https://gitlab.company.com/team/packs', 'main', 'gen/a')
    ).toBe('https://gitlab.company.com/team/packs/-/tree/main/gen/a');
  });

  it('links nothing for a host whose layout is unknown', () => {
    expect(
      buildEntryUrl('https://git.example.com/packs.git', 'main', 'generators/a')
    ).toBeNull();
  });

  it('links nothing for an address that is not an URL', () => {
    expect(buildEntryUrl('not-an-url', 'main', 'generators/a')).toBeNull();
  });
});
