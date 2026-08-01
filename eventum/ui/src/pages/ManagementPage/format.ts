/** CPU frequency label, scaled to GHz once it passes 1000 MHz. */
export function formatFreq(mhz: number): string {
  if (mhz >= 1000) return `${(mhz / 1000).toFixed(1)} GHz`;
  return `${Math.round(mhz)} MHz`;
}

/** Coarse human uptime from seconds (e.g. 2d 4h, 3h 12m). */
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
