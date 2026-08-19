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

  it('links nothing for a host whose layout is unknown', () => {
    expect(
      buildEntryUrl('https://git.example.com/packs.git', 'main', 'generators/a')
    ).toBeNull();
  });

  it('links nothing for an address that is not an URL', () => {
    expect(buildEntryUrl('not-an-url', 'main', 'generators/a')).toBeNull();
  });
});
