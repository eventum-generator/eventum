import { describe, expect, it } from 'vitest';
import { z } from 'zod';

import { PlaceholderStringSchema, orPlaceholder } from './placeholder';

/**
 * Placeholders let a non-string field hold `${params.x}` until the
 * backend substitutes it. A schema that stops accepting them turns
 * every parameterised project into an invalid one in the studio, and a
 * pattern that accepts too much lets a typo through to the backend.
 */
describe('PlaceholderStringSchema', () => {
  it.each(['${params.host}', '${secrets.token}', '${params.a.b.c}'])(
    'accepts %s',
    (value) => {
      expect(PlaceholderStringSchema.safeParse(value).success).toBe(true);
    }
  );

  it.each([
    '${params.}',
    '${param.host}',
    '${env.HOST}',
    'params.host',
    '${params.host',
    '',
  ])('rejects %s', (value) => {
    expect(PlaceholderStringSchema.safeParse(value).success).toBe(false);
  });
});

describe('orPlaceholder', () => {
  it('keeps accepting the value the wrapped schema describes', () => {
    const schema = orPlaceholder(z.number().int().min(1));

    expect(schema.parse(5)).toBe(5);
    expect(schema.safeParse(0).success).toBe(false);
  });

  it('accepts a placeholder in place of that value', () => {
    const schema = orPlaceholder(z.number());

    expect(schema.parse('${params.count}')).toBe('${params.count}');
  });

  it('does not accept an arbitrary string as one', () => {
    const schema = orPlaceholder(z.boolean());

    expect(schema.safeParse('true').success).toBe(false);
  });

  it('wraps an enum without widening it', () => {
    const schema = orPlaceholder(z.enum(['json', 'yaml']));

    expect(schema.parse('json')).toBe('json');
    expect(schema.parse('${secrets.format}')).toBe('${secrets.format}');
    expect(schema.safeParse('toml').success).toBe(false);
  });
});
