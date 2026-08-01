import { SearchQuery } from '@codemirror/search';
import { EditorState } from '@codemirror/state';

/** Documents longer than this are not scanned for matches at all. */
export const DOC_LIMIT = 200_000;

/** A scan stops once it has found this many matches. */
export const MATCH_LIMIT = 1000;

export interface MatchInfo {
  /** Matches found in the document, never above `MATCH_LIMIT`. */
  count: number;
  /** Position of the match the cursor sits on, counting from 1. */
  current: number | null;
  /** Whether the scan hit `MATCH_LIMIT` before reaching the end. */
  capped: boolean;
}

/**
 * Count the matches of `query` in the document and locate the one the
 * selection covers.
 *
 * The scan runs on every edit and on every keystroke in the query field, so
 * it is bounded at both ends: an oversized document (an opened sample or a
 * captured log) is skipped entirely, and a scan gives up after `MATCH_LIMIT`
 * matches. Returns `null` when there is nothing to count - an empty or
 * malformed query, or a document past the size limit.
 */
export function countMatches(
  state: EditorState,
  query: SearchQuery
): MatchInfo | null {
  if (!query.valid || state.doc.length > DOC_LIMIT) {
    return null;
  }

  const cursor = query.getCursor(state);
  const selection = state.selection.main;

  let count = 0;
  let current: number | null = null;

  for (let match = cursor.next(); !match.done; match = cursor.next()) {
    count++;

    if (
      match.value.from === selection.from &&
      match.value.to === selection.to
    ) {
      current = count;
    }

    if (count === MATCH_LIMIT) {
      return { count, current, capped: true };
    }
  }

  return { count, current, capped: false };
}

/**
 * Render match counts for the query field: the match under the cursor over
 * the total, `0` standing for a cursor that sits on no match.
 */
export function formatMatchCount(info: MatchInfo): string {
  const total = info.capped ? `${MATCH_LIMIT}+` : `${info.count}`;

  return `${info.current ?? 0}/${total}`;
}
