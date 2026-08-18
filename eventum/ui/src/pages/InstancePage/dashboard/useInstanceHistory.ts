import { useEffect, useRef, useState } from 'react';

import { useGeneratorStats } from '@/api/hooks/useGenerators';
import { GeneratorStats } from '@/api/routes/generators/schemas';
import type { FlowPoint } from '@/pages/MonitoringPage/history';

// Match the Monitoring rolling window (30 points + one extra raw sample so
// the derived-rate series still fills the whole window).
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
  cpuPercent: number;
}

/** Cumulative CPU time of one instance at a moment in time. */
interface CpuPoint {
  t: number;
  cpuSeconds: number;
}

/**
 * Rolling per-instance metrics history, accumulated client-side by polling
 * the generator stats endpoint while `enabled`. Instantaneous rates are
 * derived from the two most recent samples. Kept at the page shell (not the
 * tab panel) so the accumulated points survive tab switches instead of the
 * chart rebuilding from zero on every return.
 */
export function useInstanceHistory(
  instanceId: string,
  enabled: boolean
): InstanceHistory {
  const {
    data: stats,
    dataUpdatedAt,
    refetch,
  } = useGeneratorStats(instanceId, { enabled });

  useEffect(() => {
    if (!enabled) {
      return;
    }
    const interval = setInterval(() => void refetch(), POLL_MS);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled]);

  const [flow, setFlow] = useState<FlowPoint[]>([]);
  const [rates, setRates] = useState({ inputEps: 0, outputEps: 0 });
  const [cpuPercent, setCpuPercent] = useState(0);
  const prevPoint = useRef<FlowPoint | null>(null);
  const prevCpu = useRef<CpuPoint | null>(null);

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

    // CPU time is cumulative, so its share of a core over the last poll
    // interval is the only reading that reflects the load right now.
    const cpu: CpuPoint = {
      t: dataUpdatedAt,
      cpuSeconds: stats.resources.cpu_seconds,
    };
    const prevSample = prevCpu.current;
    if (prevSample) {
      const dt = (cpu.t - prevSample.t) / 1000;
      setCpuPercent(rate(cpu.cpuSeconds, prevSample.cpuSeconds, dt) * 100);
    } else {
      setCpuPercent((cpu.cpuSeconds / Math.max(stats.uptime, 1)) * 100);
    }
    prevCpu.current = cpu;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dataUpdatedAt]);

  return {
    stats,
    flow,
    inputEps: rates.inputEps,
    outputEps: rates.outputEps,
    cpuPercent,
  };
}
