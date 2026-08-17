import bytes from 'bytes';

const compact = new Intl.NumberFormat('en', {
  notation: 'compact',
  maximumFractionDigits: 1,
});

/** Compact large-number label (e.g. 12.4K). */
export function formatCompact(value: number): string {
  return compact.format(value);
}

/** Compact events-per-second label. */
export function formatEps(value: number): string {
  if (value >= 100) return Math.round(value).toLocaleString();
  if (value >= 10) return value.toFixed(1);
  return value.toFixed(2);
}

/** Bytes-per-second label from a byte rate. */
export function formatRate(bytesPerSecond: number | undefined): string {
  if (bytesPerSecond === undefined) return '-';
  return `${bytes(Math.round(bytesPerSecond), { decimalPlaces: 1 }) ?? '0 B'}/s`;
}
