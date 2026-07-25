import bytes from 'bytes';

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
