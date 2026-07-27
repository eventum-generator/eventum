import { language } from '@codemirror/language';
import { EditorState } from '@codemirror/state';
import { describe, expect, it } from 'vitest';

import { languageExtensions } from './language';

function languageOf(filePath: string): string | null {
  const state = EditorState.create({
    extensions: languageExtensions(filePath),
  });

  return state.facet(language)?.name ?? null;
}

describe('languageExtensions', () => {
  it.each([
    ['templates/event.json.jinja', 'jinja'],
    ['scripts/produce.py', 'python'],
    ['samples/hosts.json', 'json'],
    ['generator.yml', 'yaml'],
    ['generator.yaml', 'yaml'],
    ['README.md', 'markdown'],
  ])('opens %s in the %s mode', (filePath, expected) => {
    expect(languageOf(filePath)).toBe(expected);
  });

  it('opens a file of an unknown type as plain text', () => {
    expect(languageExtensions('samples/hosts.csv')).toEqual([]);
    expect(languageOf('samples/hosts.csv')).toBeNull();
  });

  it('adds the completion source to templates only', () => {
    // The mode and the completion source; every other mode ships alone.
    expect(languageExtensions('templates/event.json.jinja')).toHaveLength(2);
    expect(languageExtensions('samples/hosts.json')).toHaveLength(1);
  });
});
