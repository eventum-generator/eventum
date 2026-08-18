import { describe, expect, it } from 'vitest';

import { getGeneratorProjectExportUrl } from '.';

describe('getGeneratorProjectExportUrl', () => {
  it('points at the export endpoint', () => {
    expect(getGeneratorProjectExportUrl('demo')).toBe(
      '/api/generator-configs/demo/export'
    );
  });

  it('repeats the key for every excluded entry', () => {
    expect(getGeneratorProjectExportUrl('demo', ['output', 'tmp'])).toBe(
      '/api/generator-configs/demo/export?exclude=output&exclude=tmp'
    );
  });

  it('escapes what carries meaning in a URL', () => {
    // A '#' would cut the URL short; a space in a query value ships as
    // '+', which the backend reads back as a space.
    expect(getGeneratorProjectExportUrl('my project', ['out #1'])).toBe(
      '/api/generator-configs/my%20project/export?exclude=out+%231'
    );
  });
});
