/**
 * Position the selection takes after the plugin at `removed` is dropped
 * from a list that is `length` items long afterwards.
 *
 * Removing a plugin that sits before the selected one keeps the same
 * plugin selected by following it one position up. Removing the selected
 * plugin itself keeps the position, which now holds its neighbour, and
 * clamps it into the shortened list.
 */
export function nextSelectedIndex(
  selected: number,
  removed: number,
  length: number
): number {
  if (removed < selected) {
    return selected - 1;
  }

  return Math.min(selected, Math.max(length - 1, 0));
}
