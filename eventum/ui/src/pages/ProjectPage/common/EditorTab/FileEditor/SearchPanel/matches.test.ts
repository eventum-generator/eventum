import { SearchQuery } from '@codemirror/search';
import { EditorState } from '@codemirror/state';
import { describe, expect, it } from 'vitest';

import {
  DOC_LIMIT,
  MATCH_LIMIT,
  countMatches,
  formatMatchCount,
} from './matches';

function stateOf(doc: string, selection?: [number, number]): EditorState {
  return EditorState.create({
    doc,
    selection: selection && { anchor: selection[0], head: selection[1] },
  });
}

describe('countMatches', () => {
  it('counts every occurrence in the document', () => {
    expect(
      countMatches(stateOf('a b a b a'), new SearchQuery({ search: 'a' }))
    ).toEqual({ count: 3, current: null, capped: false });
  });

  it('locates the match the selection covers', () => {
    expect(
      countMatches(
        stateOf('a b a b a', [4, 5]),
        new SearchQuery({ search: 'a' })
      )
    ).toEqual({ count: 3, current: 2, capped: false });
  });

  it('reports no current match when the selection only touches one', () => {
    // Caret parked at the start of the second match, nothing selected.
    expect(
      countMatches(
        stateOf('a b a b a', [4, 4]),
        new SearchQuery({ search: 'a' })
      )?.current
    ).toBeNull();
  });

  it('honours case sensitivity', () => {
    const state = stateOf('Ab ab AB');

    expect(countMatches(state, new SearchQuery({ search: 'ab' }))?.count).toBe(
      3
    );
    expect(
      countMatches(
        state,
        new SearchQuery({ search: 'ab', caseSensitive: true })
      )?.count
    ).toBe(1);
  });

  it('honours whole-word matching', () => {
    const state = stateOf('log logger log');

    expect(countMatches(state, new SearchQuery({ search: 'log' }))?.count).toBe(
      3
    );
    expect(
      countMatches(state, new SearchQuery({ search: 'log', wholeWord: true }))
        ?.count
    ).toBe(2);
  });

  it('counts regular expression matches', () => {
    expect(
      countMatches(
        stateOf('id=1 id=22 name=x'),
        new SearchQuery({ search: String.raw`id=\d+`, regexp: true })
      )?.count
    ).toBe(2);
  });

  it('skips an empty query', () => {
    expect(
      countMatches(stateOf('a b a'), new SearchQuery({ search: '' }))
    ).toBeNull();
  });

  it('skips a malformed regular expression', () => {
    expect(
      countMatches(
        stateOf('a b a'),
        new SearchQuery({ search: 'a(', regexp: true })
      )
    ).toBeNull();
  });

  it('gives up once the scan hits the match limit', () => {
    expect(
      countMatches(
        stateOf('a'.repeat(MATCH_LIMIT + 1)),
        new SearchQuery({ search: 'a' })
      )
    ).toEqual({ count: MATCH_LIMIT, current: null, capped: true });
  });

  it('skips a document past the size limit', () => {
    expect(
      countMatches(
        stateOf('x'.repeat(DOC_LIMIT + 1)),
        new SearchQuery({ search: 'q' })
      )
    ).toBeNull();
  });

  it('terminates on a pattern that matches the empty string', () => {
    expect(
      countMatches(
        stateOf('ab'),
        new SearchQuery({ search: 'x*', regexp: true })
      )?.capped
    ).toBe(false);
  });
});

describe('formatMatchCount', () => {
  it('reads as the current match over the total', () => {
    expect(formatMatchCount({ count: 17, current: 3, capped: false })).toBe(
      '3/17'
    );
  });

  it('falls back to zero when the cursor sits on no match', () => {
    expect(formatMatchCount({ count: 17, current: null, capped: false })).toBe(
      '0/17'
    );
  });

  it('marks a capped total as open-ended', () => {
    expect(
      formatMatchCount({ count: MATCH_LIMIT, current: 3, capped: true })
    ).toBe(`3/${MATCH_LIMIT}+`);
  });
});
