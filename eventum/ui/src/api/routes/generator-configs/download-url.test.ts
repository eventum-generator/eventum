import { describe, expect, it } from 'vitest';

import { getGeneratorFileDownloadUrl } from '.';

describe('getGeneratorFileDownloadUrl', () => {
  it('points at the file endpoint in download mode', () => {
    expect(getGeneratorFileDownloadUrl('demo', 'output/events.json')).toBe(
      '/api/generator-configs/demo/file/output/events.json?download=true'
    );
  });

  it('escapes what carries meaning in a URL, keeping separators', () => {
    // A '#' would cut the path short and a '?' would start the query,
    // so a file named with either would be requested as a different one.
    expect(
      getGeneratorFileDownloadUrl('my project', 'out/re port #1.json')
    ).toBe(
      '/api/generator-configs/my%20project/file/out/re%20port%20%231.json' +
        '?download=true'
    );
  });

  it('encodes a non-ASCII name', () => {
    expect(getGeneratorFileDownloadUrl('demo', 'события.log')).toBe(
      '/api/generator-configs/demo/file/' +
        '%D1%81%D0%BE%D0%B1%D1%8B%D1%82%D0%B8%D1%8F.log?download=true'
    );
  });
});
