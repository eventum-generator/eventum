import { describe, expect, it } from 'vitest';

import { previewLanguage } from './preview-language';

describe('previewLanguage', () => {
  it('highlights templates with the jinja grammar', () => {
    expect(previewLanguage('templates/order.json.jinja')).toBe('jinja');
  });

  it('highlights scripts as python', () => {
    expect(previewLanguage('scripts/produce.py')).toBe('python');
  });

  it('maps an extension to the grammar loaded for it', () => {
    expect(previewLanguage('generator.yml')).toBe('yaml');
  });

  it('falls back to plain text for a grammar that is not loaded', () => {
    expect(previewLanguage('samples/hosts.parquet')).toBe('text');
    expect(previewLanguage('LICENSE')).toBe('text');
  });
});
