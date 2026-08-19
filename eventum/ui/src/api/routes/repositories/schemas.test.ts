import { describe, expect, it } from 'vitest';

import { CatalogSchema } from './schemas';

const CATALOG = {
  revision: 'a'.repeat(40),
  refreshed_at: '2026-08-19T21:56:52.225108Z',
  committed_at: '2026-07-31T12:24:16+03:00',
  author: 'Author',
  entries: [
    {
      name: 'web-nginx',
      path: 'generators/web-nginx',
      title: 'Nginx Access Logs',
      summary: 'Produces nginx access log entries.',
      file_count: 3,
      size: 1024,
      installed_as: [
        {
          project: 'nginx',
          revision: 'a'.repeat(40),
          installed_at: '2026-08-19T21:56:52.225108Z',
          outdated: false,
        },
      ],
    },
  ],
};

describe('CatalogSchema', () => {
  it('reads a commit authored outside UTC', () => {
    // A repository is authored wherever its author is, so the moment
    // a commit was made arrives with the offset it was made in.
    expect(CatalogSchema.safeParse(CATALOG).success).toBe(true);
  });

  it('reads a commit authored in UTC', () => {
    expect(
      CatalogSchema.safeParse({
        ...CATALOG,
        committed_at: '2026-07-31T09:24:16Z',
      }).success
    ).toBe(true);
  });

  it('refuses a moment carrying no timezone', () => {
    expect(
      CatalogSchema.safeParse({
        ...CATALOG,
        committed_at: '2026-07-31T09:24:16',
      }).success
    ).toBe(false);
  });
});
