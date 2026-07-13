import { useEffect, useRef, useState } from 'react';

import { APIError } from '@/api/errors';
import { useGeneratorStats } from '@/api/hooks/useGenerators';
import { GeneratorStats } from '@/api/routes/generators/schemas';
import type { FlowPoint } from '@/pages/MonitoringPage/history';

// Match the Monitoring rolling window (30 points + one extra raw sample so
// derived-rate series still fill the window).
const RAW_POINTS = 31;
const POLL_MS = 5000;

/** Cumulative pipeline counters of one instance at a moment in time. */
function toFlowPoint(t: number, s: GeneratorStats): FlowPoint {
  let writeFailed = 0;
  let formatFailed = 0;
  for (const o of s.output) {
    writeFailed += o.write_failed;
    formatFailed += o.format_failed;
  }
  return {
    t,
    generated: s.total_generated,
    produced: s.event.produced,
    written: s.total_written,
    dropped: s.event.dropped,
    produceFailed: s.event.produce_failed,
    writeFailed,
    formatFailed,
  };
}

function rate(curr: number, prev: number, dtSeconds: number): number {
  return dtSeconds > 0 ? Math.max(0, (curr - prev) / dtSeconds) : 0;
}

interface InstanceHistory {
  stats: GeneratorStats | undefined;
  flow: FlowPoint[];
  inputEps: number;
  outputEps: number;
  failing: boolean;
  isError: boolean;
  statusCode: number | undefined;
}

/**
 * Rolling per-instance metrics history, accumulated client-side from polling
 * the generator stats endpoint. Instantaneous rates are derived from the two
 * most recent samples; history is ephemeral and resets on navigation. Only
 * mount this while the instance runs - polling stops when it unmounts.
 */
export function useInstanceHistory(instanceId: string): InstanceHistory {
  const {
    data: stats,
    dataUpdatedAt,
    isError,
    error,
    refetch,
  } = useGeneratorStats(instanceId);

  useEffect(() => {
    const interval = setInterval(() => void refetch(), POLL_MS);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const [flow, setFlow] = useState<FlowPoint[]>([]);
  const [rates, setRates] = useState({ inputEps: 0, outputEps: 0 });
  const prevPoint = useRef<FlowPoint | null>(null);

  useEffect(() => {
    if (!stats || dataUpdatedAt === 0) {
      return;
    }

    const point = toFlowPoint(dataUpdatedAt, stats);
    const prev = prevPoint.current;
    if (prev) {
      const dt = (point.t - prev.t) / 1000;
      setRates({
        inputEps: rate(point.generated, prev.generated, dt),
        outputEps: rate(point.written, prev.written, dt),
      });
    } else {
      setRates({ inputEps: stats.input_eps, outputEps: stats.output_eps });
    }
    prevPoint.current = point;
    setFlow((buffer) => [...buffer, point].slice(-RAW_POINTS));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dataUpdatedAt]);

  const failing = stats
    ? stats.event.produce_failed +
        stats.output.reduce((n, o) => n + o.write_failed + o.format_failed, 0) >
      0
    : false;

  const statusCode =
    isError && error instanceof APIError ? error.response?.status : undefined;

  return {
    stats,
    flow,
    inputEps: rates.inputEps,
    outputEps: rates.outputEps,
    failing,
    isError,
    statusCode,
  };
}
