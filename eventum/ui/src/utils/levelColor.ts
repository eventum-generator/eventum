/** Semantic color for a utilisation percentage against warn/bad thresholds.
 *  Shared by every load readout so the same percentage reads the same way
 *  wherever it appears. */
export function levelColor(pct: number, warn: number, bad: number): string {
  if (pct >= bad) return 'var(--mantine-color-red-text)';
  if (pct >= warn) return 'var(--mantine-color-yellow-text)';
  return 'var(--mantine-color-green-text)';
}

/** Thresholds the app applies to host resources. */
export const CPU_THRESHOLDS = { warn: 60, bad: 85 };
export const MEMORY_THRESHOLDS = { warn: 70, bad: 90 };

/** Descriptors run out abruptly, so their thresholds warn earlier. */
export const FD_THRESHOLDS = { warn: 50, bad: 80 };
