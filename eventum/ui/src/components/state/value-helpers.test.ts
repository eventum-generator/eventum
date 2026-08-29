import { describe, expect, it } from 'vitest';

import {
  formatValuePreview,
  getValueType,
  isSimpleValue,
  typeBadgeColor,
} from './value-helpers';

/**
 * The state tables show a value the generator put there, of any JSON
 * shape. The type decides whether the row can be edited inline or opens
 * the editor, and the preview is all the user sees of a value until
 * then, so both have to answer for `null`, an empty collection and a
 * nested object rather than only for a string.
 */
describe('getValueType', () => {
  it.each([
    [null, 'null'],
    [[], 'array'],
    [[1, 2], 'array'],
    ['text', 'string'],
    [1, 'number'],
    [true, 'boolean'],
    [{}, 'object'],
  ])('names %o as %s', (value, expected) => {
    expect(getValueType(value)).toBe(expected);
  });

  it('does not confuse an array with an object', () => {
    expect(getValueType([])).not.toBe(getValueType({}));
  });
});

describe('formatValuePreview', () => {
  it.each([
    [null, 'null'],
    [undefined, 'undefined'],
    ['text', '"text"'],
    ['', '""'],
    [0, '0'],
    [-1.5, '-1.5'],
    [false, 'false'],
  ])('previews %o as %s', (value, expected) => {
    expect(formatValuePreview(value)).toBe(expected);
  });

  it('counts the members of a collection instead of listing them', () => {
    expect(formatValuePreview([1, 2, 3])).toBe('[3 items]');
    expect(formatValuePreview([])).toBe('[0 items]');
    expect(formatValuePreview({ a: 1, b: 2 })).toBe('{2 keys}');
    expect(formatValuePreview({})).toBe('{0 keys}');
  });

  it('counts only the keys of the top level', () => {
    expect(formatValuePreview({ a: { b: 1, c: 2 } })).toBe('{1 keys}');
  });
});

describe('isSimpleValue', () => {
  it.each([[null], [undefined], ['text'], [0], [false]])(
    'treats %o as editable inline',
    (value) => {
      expect(isSimpleValue(value)).toBe(true);
    }
  );

  it.each([[[]], [{}], [[1]], [{ a: 1 }]])(
    'sends %o to the editor',
    (value) => {
      expect(isSimpleValue(value)).toBe(false);
    }
  );
});

describe('typeBadgeColor', () => {
  it.each(['string', 'number', 'boolean', 'object', 'array', 'null'])(
    'gives %s a colour of its own',
    (type) => {
      expect(typeBadgeColor(type)).toBeTruthy();
    }
  );

  it('distinguishes the types a value can be shown as', () => {
    const colors = ['string', 'number', 'boolean', 'object', 'array'].map(
      (type) => typeBadgeColor(type)
    );

    expect(new Set(colors).size).toBe(colors.length);
  });

  it('falls back to the neutral colour for a type it has none for', () => {
    expect(typeBadgeColor('function')).toBe('gray');
  });
});
