import { GeneratorStats } from '@/api/routes/generators/schemas';

/** Fleet-wide sum of cumulative pipeline counters across generators. */
export interface FlowAgg {
  generated: number;
  produced: number;
  written: number;
  dropped: number;
  produceFailed: number;
  writeFailed: number;
  formatFailed: number;
}

export function aggregateFlow(stats: GeneratorStats[]): FlowAgg {
  const agg: FlowAgg = {
    generated: 0,
    produced: 0,
    written: 0,
    dropped: 0,
    produceFailed: 0,
    writeFailed: 0,
    formatFailed: 0,
  };
  for (const s of stats) {
    agg.generated += s.total_generated;
    agg.produced += s.event.produced;
    agg.dropped += s.event.dropped;
    agg.produceFailed += s.event.produce_failed;
    agg.written += s.total_written;
    for (const o of s.output) {
      agg.writeFailed += o.write_failed;
      agg.formatFailed += o.format_failed;
    }
  }
  return agg;
}

export function formatUptime(seconds: number): string {
  const s = Math.max(0, Math.floor(seconds));
  const d = Math.floor(s / 86_400);
  const h = Math.floor((s % 86_400) / 3600);
  const m = Math.floor((s % 3600) / 60);
  if (d > 0) return `${d}d ${h}h`;
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m`;
  return `${s}s`;
}
