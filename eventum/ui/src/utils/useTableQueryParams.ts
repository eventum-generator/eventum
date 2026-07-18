import { useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';

type ParamValue = string | string[] | null | undefined;

/**
 * URL-backed table filters. Read current values from the returned
 * `searchParams`; write with `setParams`, which merges the given keys into the
 * current query string (untouched keys survive) in a single, history-replacing
 * navigation - so typing a filter does not spam the back stack and a shared URL
 * restores every filter.
 *
 * A key set to `null` / `''` / `[]` is removed, keeping URLs clean; a key set
 * to `undefined` is left unchanged. Lists serialize as comma-separated values.
 * Passing several keys in one call avoids clobbering when a single handler
 * changes more than one filter.
 */
export function useTableQueryParams() {
  const [searchParams, setSearchParams] = useSearchParams();

  const setParams = useCallback(
    (updates: Record<string, ParamValue>) => {
      setSearchParams(
        (prev) => {
          const params = new URLSearchParams(prev);

          for (const [key, value] of Object.entries(updates)) {
            if (value === undefined) {
              continue;
            }

            const isEmpty =
              value === null ||
              value === '' ||
              (Array.isArray(value) && value.length === 0);

            if (isEmpty) {
              params.delete(key);
            } else {
              params.set(key, Array.isArray(value) ? value.join(',') : value);
            }
          }

          return params;
        },
        { replace: true }
      );
    },
    [setSearchParams]
  );

  return { searchParams, setParams };
}
