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

/**
 * Tick label for a chart axis: the bare number, since the unit belongs to
 * the reading above the chart. Axis room is narrow, so a tick that spells
 * out decimals and a unit ends up against the edge of the panel.
 */
export function formatAxis(value: number): string {
  if (value === 0) return '0';
  if (value >= 1000) return compact.format(value);
  if (value >= 10) return String(Math.round(value));
  return value.toFixed(1);
}

/** Tick label for a byte-rate axis: no decimals, no unit suffix. */
export function formatBytesAxis(value: number): string {
  return bytes(Math.round(value), { decimalPlaces: 0 }) ?? '0';
}
