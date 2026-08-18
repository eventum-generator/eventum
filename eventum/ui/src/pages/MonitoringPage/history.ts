import { useEffect, useRef, useState } from 'react';

import { aggregateFlow } from './metrics';
import { GeneratorStats } from '@/api/routes/generators/schemas';
import { InstanceInfo } from '@/api/routes/instance/schemas';

/**
 * Rolling metrics history kept client-side, starting from the moment the
 * page mounts. The Monitoring page already polls the snapshot endpoints
 * every 10s; we accumulate each poll into bounded buffers and derive
 * instantaneous rates from consecutive samples. History is intentionally
 * ephemeral - it resets on refresh/navigation.
 */

const STEP_MS = 5000;

// Default display window: ~2.5 minutes at a 5s poll cadence. Charts behave
// like the Task Manager graphs - points enter from the right and crawl left,
// never stretching to fill the width.
export const MAX_POINTS = 30;

/** Selectable chart windows, in points at the 5s poll cadence. */
export const WINDOW_OPTIONS = [
  { value: '30', label: '2.5 min' },
  { value: '120', label: '10 min' },
  { value: '360', label: '30 min' },
];

const LONGEST_WINDOW = 360;

// Buffers hold the longest selectable window plus one extra raw sample:
// derived-rate series consume consecutive pairs and thus yield one fewer
// point, so the extra sample lets them still fill the whole window instead of
// leaving an empty leading slot. Switching to a longer window shows what has
// been collected so far and fills in from there.
const RAW_POINTS = LONGEST_WINDOW + 1;

export interface ResourcePoint {
  t: number;
  cpu: number;
  memPct: number;
  appMem: number;
  diskRead: number;
  diskWrite: number;
  netRecv: number;
  netSent: number;
}

export interface FlowPoint {
  t: number;
  generated: number;
  produced: number;
  written: number;
  dropped: number;
  produceFailed: number;
  writeFailed: number;
  formatFailed: number;
}

/** Instantaneous values derived from the two most recent samples. */
export interface CurrentMetrics {
  inputEps: number;
  producedEps: number;
  outputEps: number;
  failEps: number;
  failing: boolean;
  diskReadBps: number;
  diskWriteBps: number;
  netRecvBps: number;
  netSentBps: number;
}

/**
 * One poll of per-generator cumulative output. `written` maps a generator id
 * to its `total_written` counter at that instant; per-instance rates are
 * derived from consecutive polls. Ids absent from a poll were not running
 * then.
 */
export interface LoadPoint {
  t: number;
  time: string;
  written: Record<string, number>;
}

/**
 * What one generator occupied at the moment of a poll. The counters are
 * cumulative since it started; the queue figures are instantaneous.
 */
export interface InstanceUsage {
  cpuSeconds: number;
  runDelaySeconds: number;
  diskWrite: number;
  netSent: number;
  threads: number;
  written: number;
  failed: number;
  queueSize: number;
  queueMaxsize: number;
  queueBytes: number;
  queueMaxBytes: number | null;
}

/** One poll of what every running generator occupied, keyed by its id. */
export interface UsagePoint {
  t: number;
  usage: Record<string, InstanceUsage>;
}

function cap<T>(buffer: T[], next: T, size = MAX_POINTS): T[] {
  const kept =
    buffer.length >= size
      ? buffer.slice(buffer.length - size + 1)
      : buffer.slice();
  kept.push(next);
  return kept;
}

function rate(curr: number, prev: number, dtSeconds: number): number {
  if (dtSeconds <= 0) return 0;
  return Math.max(0, (curr - prev) / dtSeconds);
}

interface UseMetricsHistoryArgs {
  instanceInfo: InstanceInfo | undefined;
  instanceUpdatedAt: number;
  stats: GeneratorStats[];
  statsUpdatedAt: number;
}

export function useMetricsHistory({
  instanceInfo,
  instanceUpdatedAt,
  stats,
  statsUpdatedAt,
}: UseMetricsHistoryArgs): {
  resources: ResourcePoint[];
  flow: FlowPoint[];
  load: LoadPoint[];
  usage: UsagePoint[];
  current: CurrentMetrics;
} {
  const [resources, setResources] = useState<ResourcePoint[]>([]);
  const [flow, setFlow] = useState<FlowPoint[]>([]);
  const [load, setLoad] = useState<LoadPoint[]>([]);
  const [usage, setUsage] = useState<UsagePoint[]>([]);
  const [flowCurrent, setFlowCurrent] = useState({
    inputEps: 0,
    producedEps: 0,
    outputEps: 0,
    failEps: 0,
    failing: false,
  });
  const [resCurrent, setResCurrent] = useState({
    diskReadBps: 0,
    diskWriteBps: 0,
    netRecvBps: 0,
    netSentBps: 0,
  });
  const prevResource = useRef<ResourcePoint | null>(null);
  const prevFlow = useRef<FlowPoint | null>(null);

  useEffect(() => {
    if (!instanceInfo || instanceUpdatedAt === 0) return;

    const memPct =
      instanceInfo.memory_total_bytes > 0
        ? (instanceInfo.memory_used_bytes / instanceInfo.memory_total_bytes) *
          100
        : 0;
    const point: ResourcePoint = {
      t: instanceUpdatedAt,
      cpu: instanceInfo.cpu_percent,
      memPct,
      appMem: instanceInfo.process_memory_bytes,
      diskRead: instanceInfo.disk_read_bytes,
      diskWrite: instanceInfo.disk_written_bytes,
      netRecv: instanceInfo.network_received_bytes,
      netSent: instanceInfo.network_sent_bytes,
    };
    const prev = prevResource.current;
    const dt = prev ? (point.t - prev.t) / 1000 : 0;

    setResCurrent({
      diskReadBps: prev ? rate(point.diskRead, prev.diskRead, dt) : 0,
      diskWriteBps: prev ? rate(point.diskWrite, prev.diskWrite, dt) : 0,
      netRecvBps: prev ? rate(point.netRecv, prev.netRecv, dt) : 0,
      netSentBps: prev ? rate(point.netSent, prev.netSent, dt) : 0,
    });
    prevResource.current = point;
    setResources((buffer) => cap(buffer, point, RAW_POINTS));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [instanceUpdatedAt]);

  useEffect(() => {
    if (statsUpdatedAt === 0) return;

    const agg = aggregateFlow(stats);
    const point: FlowPoint = { t: statsUpdatedAt, ...agg };
    const prev = prevFlow.current;
    const dt = prev ? (point.t - prev.t) / 1000 : 0;

    const failed = agg.produceFailed + agg.writeFailed + agg.formatFailed;
    const failedBefore = prev
      ? prev.produceFailed + prev.writeFailed + prev.formatFailed
      : 0;

    setFlowCurrent({
      inputEps: prev ? rate(point.generated, prev.generated, dt) : 0,
      producedEps: prev ? rate(point.produced, prev.produced, dt) : 0,
      outputEps: prev ? rate(point.written, prev.written, dt) : 0,
      failEps: prev ? rate(failed, failedBefore, dt) : 0,
      failing: failed > 0,
    });
    prevFlow.current = point;
    setFlow((buffer) => cap(buffer, point, RAW_POINTS));

    const written: Record<string, number> = {};
    for (const s of stats) written[s.id] = s.total_written;
    setLoad((buffer) =>
      cap(
        buffer,
        { t: statsUpdatedAt, time: clock(statsUpdatedAt), written },
        RAW_POINTS
      )
    );

    const usagePoint: Record<string, InstanceUsage> = {};
    for (const s of stats) {
      let failed = s.event.produce_failed;
      for (const o of s.output) failed += o.write_failed + o.format_failed;

      usagePoint[s.id] = {
        cpuSeconds: s.resources.cpu_seconds,
        runDelaySeconds: s.resources.run_delay_seconds,
        diskWrite: s.resources.disk_written_bytes,
        netSent: s.resources.network_sent_bytes,
        threads: s.resources.thread_count,
        written: s.total_written,
        failed,
        queueSize: s.resources.queues.events.size,
        queueMaxsize: s.resources.queues.events.maxsize,
        queueBytes: s.resources.queues.events.size_bytes,
        queueMaxBytes: s.resources.queues.events.max_bytes,
      };
    }
    setUsage((buffer) =>
      cap(buffer, { t: statsUpdatedAt, usage: usagePoint }, RAW_POINTS)
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statsUpdatedAt]);

  return {
    resources,
    flow,
    load,
    usage,
    current: { ...flowCurrent, ...resCurrent },
  };
}

function pad(n: number): string {
  return String(n).padStart(2, '0');
}

function clock(t: number): string {
  const d = new Date(t);
  return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

/**
 * Left-pad a series to a fixed length with empty (null-valued) slots. Real
 * points sit on the right; the line crawls left as history fills, then
 * scrolls - the chart width stays constant regardless of point count.
 */
export function fixedWindow<T extends { t: number; time: string }>(
  data: T[],
  size: number,
  empty: Omit<T, 't' | 'time'>
): T[] {
  const trimmed = data.length > size ? data.slice(data.length - size) : data;
  const padCount = size - trimmed.length;
  if (padCount <= 0) return trimmed;

  const baseT = trimmed[0]?.t ?? 0;
  const head: T[] = [];
  for (let k = padCount; k > 0; k--) {
    const t = baseT - k * STEP_MS;
    head.push({ t, time: clock(t), ...empty } as T);
  }
  return [...head, ...trimmed];
}

export interface ThroughputDatum {
  t: number;
  time: string;
  input: number | null;
  output: number | null;
}

export function throughputData(flow: FlowPoint[]): ThroughputDatum[] {
  const out: ThroughputDatum[] = [];
  for (let i = 1; i < flow.length; i++) {
    const curr = flow[i];
    const prev = flow[i - 1];
    if (!curr || !prev) continue;

    const dt = (curr.t - prev.t) / 1000;
    out.push({
      t: curr.t,
      time: clock(curr.t),
      input: rate(curr.generated, prev.generated, dt),
      output: rate(curr.written, prev.written, dt),
    });
  }
  return out;
}

export interface ErrorDatum {
  t: number;
  time: string;
  event: number | null;
  output: number | null;
}

/** Failure rates grouped by pipeline stage (event vs output). */
export function errorData(flow: FlowPoint[]): ErrorDatum[] {
  const rows: ErrorDatum[] = [];
  for (let i = 1; i < flow.length; i++) {
    const curr = flow[i];
    const prev = flow[i - 1];
    if (!curr || !prev) continue;

    const dt = (curr.t - prev.t) / 1000;
    rows.push({
      t: curr.t,
      time: clock(curr.t),
      event: rate(curr.produceFailed, prev.produceFailed, dt),
      output: rate(
        curr.writeFailed + curr.formatFailed,
        prev.writeFailed + prev.formatFailed,
        dt
      ),
    });
  }
  return rows;
}

type GaugeKey = 'cpu' | 'memPct';
type CounterKey = 'diskRead' | 'diskWrite' | 'netRecv' | 'netSent';

export interface SeriesPoint {
  t: number;
  time: string;
  value: number | null;
}

/** Gauge metric (cpu/memory percent) as timed points for a chart. */
export function gaugePoints(
  resources: ResourcePoint[],
  key: GaugeKey
): SeriesPoint[] {
  return resources.map((r) => ({ t: r.t, time: clock(r.t), value: r[key] }));
}

export interface DualPoint {
  t: number;
  time: string;
  in: number | null;
  out: number | null;
}

/** Two cumulative counters as instantaneous in/out per-second rates. */
export function dualRateData(
  resources: ResourcePoint[],
  inKey: CounterKey,
  outKey: CounterKey
): DualPoint[] {
  const rows: DualPoint[] = [];
  for (let i = 1; i < resources.length; i++) {
    const curr = resources[i];
    const prev = resources[i - 1];
    if (!curr || !prev) continue;

    const dt = (curr.t - prev.t) / 1000;
    rows.push({
      t: curr.t,
      time: clock(curr.t),
      in: rate(curr[inKey], prev[inKey], dt),
      out: rate(curr[outKey], prev[outKey], dt),
    });
  }
  return rows;
}

export interface InstanceUsageRow {
  id: string;
  cpuPercent: number;
  waitPercent: number;
  diskWriteBps: number;
  netSentBps: number;
  threads: number;
  outputEps: number;
  failEps: number;
  queueSize: number;
  queueMaxsize: number;
  queueBytes: number;
  queueMaxBytes: number | null;
  /** Fill level of the events queue, the fuller of its two limits. */
  queuePercent: number;
}

/** Fill level of a queue: the fuller of the batches and the bytes it holds. */
function queueFill(usage: InstanceUsage): number {
  const batches =
    usage.queueMaxsize > 0 ? (usage.queueSize / usage.queueMaxsize) * 100 : 0;
  const bytes = usage.queueMaxBytes
    ? (usage.queueBytes / usage.queueMaxBytes) * 100
    : 0;
  return Math.max(batches, bytes);
}

/**
 * What each running generator occupies right now, heaviest first. The CPU and
 * the waiting share come from the two most recent polls: both counters are
 * cumulative, so only their growth over an interval says what a generator
 * costs at the moment. A generator absent from the earlier poll contributes
 * nothing to the rates until the next one.
 */
export function instanceUsageRows(usage: UsagePoint[]): InstanceUsageRow[] {
  const [prev, curr] = usage.slice(-2);
  if (!curr || !prev) return [];

  const dt = (curr.t - prev.t) / 1000;
  const rows: InstanceUsageRow[] = [];

  for (const [id, now] of Object.entries(curr.usage)) {
    const before = prev.usage[id];
    rows.push({
      id,
      cpuPercent: before
        ? rate(now.cpuSeconds, before.cpuSeconds, dt) * 100
        : 0,
      waitPercent: before
        ? rate(now.runDelaySeconds, before.runDelaySeconds, dt) * 100
        : 0,
      diskWriteBps: before ? rate(now.diskWrite, before.diskWrite, dt) : 0,
      netSentBps: before ? rate(now.netSent, before.netSent, dt) : 0,
      threads: now.threads,
      outputEps: before ? rate(now.written, before.written, dt) : 0,
      failEps: before ? rate(now.failed, before.failed, dt) : 0,
      queueSize: now.queueSize,
      queueMaxsize: now.queueMaxsize,
      queueBytes: now.queueBytes,
      queueMaxBytes: now.queueMaxBytes,
      queuePercent: queueFill(now),
    });
  }

  return rows.sort(
    (a, b) => b.cpuPercent - a.cpuPercent || a.id.localeCompare(b.id)
  );
}

export interface StageDatum {
  t: number;
  time: string;
  input: number | null;
  event: number | null;
  output: number | null;
}

/**
 * The rate at which each pipeline stage moved events, so a stage that lets
 * fewer through than the one before it - the point where the pipeline narrows
 * - is visible next to the same load split by instance.
 */
export function stageData(flow: FlowPoint[]): StageDatum[] {
  const rows: StageDatum[] = [];
  for (let i = 1; i < flow.length; i++) {
    const curr = flow[i];
    const prev = flow[i - 1];
    if (!curr || !prev) continue;

    const dt = (curr.t - prev.t) / 1000;
    rows.push({
      t: curr.t,
      time: clock(curr.t),
      input: rate(curr.generated, prev.generated, dt),
      event: rate(curr.produced, prev.produced, dt),
      output: rate(curr.written, prev.written, dt),
    });
  }
  return rows;
}

export interface InstanceRateRow {
  t: number;
  time: string;
  rates: Record<string, number>;
}

/**
 * Per-generator output rate (events/s) derived from consecutive cumulative
 * `total_written` samples - the same delta basis the throughput chart uses,
 * so per-instance rates sum to the fleet output rate. A generator absent
 * from the previous sample contributes 0 for that interval.
 */
export function instanceLoadData(load: LoadPoint[]): InstanceRateRow[] {
  const rows: InstanceRateRow[] = [];
  for (let i = 1; i < load.length; i++) {
    const curr = load[i];
    const prev = load[i - 1];
    if (!curr || !prev) continue;

    const dt = (curr.t - prev.t) / 1000;
    const rates: Record<string, number> = {};
    for (const id of Object.keys(curr.written)) {
      const prevVal = prev.written[id];
      rates[id] =
        prevVal === undefined ? 0 : rate(curr.written[id] ?? 0, prevVal, dt);
    }
    rows.push({ t: curr.t, time: clock(curr.t), rates });
  }
  return rows;
}

/** Band holding everything past the top of the ranking. */
export const OTHER_BAND = 'Other instances';

/**
 * Per-instance bands for the load chart, ranked by what each instance
 * currently writes and cut to `keep` bands: the rest are summed into one
 * band, so a fleet of fifty stays a readable chart instead of fifty stripes
 * a pixel wide.
 */
export function instanceBands(
  load: LoadPoint[],
  keep: number
): { ids: string[]; rows: InstanceRateRow[] } {
  const derived = instanceLoadData(load);

  const totals = new Map<string, number>();
  for (const row of derived)
    for (const [id, eps] of Object.entries(row.rates))
      totals.set(id, (totals.get(id) ?? 0) + eps);

  const ranked = [...totals.entries()]
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
    .map(([id]) => id);

  if (ranked.length <= keep) return { ids: ranked, rows: derived };

  const kept = new Set(ranked.slice(0, keep));
  const rows = derived.map((row) => {
    const rates: Record<string, number> = {};
    let other = 0;
    for (const [id, eps] of Object.entries(row.rates)) {
      if (kept.has(id)) rates[id] = eps;
      else other += eps;
    }
    rates[OTHER_BAND] = other;
    return { ...row, rates };
  });

  return { ids: [...ranked.slice(0, keep), OTHER_BAND], rows };
}
