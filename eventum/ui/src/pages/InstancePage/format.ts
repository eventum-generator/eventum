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

/** Coarse human uptime from seconds (e.g. 2h 14m). */
export function formatUptime(seconds: number): string {
  const s = Math.max(0, Math.floor(seconds));
  const d = Math.floor(s / 86_400);
  const h = Math.floor((s % 86_400) / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  if (d > 0) return `${d}d ${h}h`;
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m ${String(sec).padStart(2, '0')}s`;
  return `${sec}s`;
}
