import { AreaChart } from '@mantine/charts';
import { Box, Center, Group, Paper, Stack, Text } from '@mantine/core';
import { FC, useMemo } from 'react';

import { Metric } from './Metric';
import { SectionLabel } from './SectionLabel';
import { formatEps } from './format';
import {
  InstanceRateRow,
  LoadPoint,
  MAX_POINTS,
  fixedWindow,
  instanceLoadData,
} from './history';

// Categorical palette for per-instance bands. Brand hues lead; the rest are
// distinct mid-saturation colours that stay legible on both themes. Semantic
// red is reserved for failures and deliberately omitted.
const PALETTE = [
  'var(--ev-accent)',
  'var(--ev-cyan)',
  '#3fb950',
  '#d29922',
  '#4d9fff',
  '#c77dff',
  '#2dd4bf',
  '#fb923c',
];
const FALLBACK = 'var(--ev-accent)';

interface InstanceLoadProps {
  load: LoadPoint[];
}

/**
 * Per-instance share of the fleet's output load. A stacked area over the
 * rolling window shows each running generator's output rate composing the
 * total envelope; the ranked legend below gives the exact per-instance rate
 * and its percentage of the current total. Rates are derived from cumulative
 * output deltas (matching the throughput chart), and colours are keyed to
 * generator id so a band keeps its colour across polls.
 */
export const InstanceLoad: FC<InstanceLoadProps> = ({ load }) => {
  const derived = useMemo(() => instanceLoadData(load), [load]);

  const ids = useMemo(() => {
    const set = new Set<string>();
    for (const row of derived)
      for (const id of Object.keys(row.rates)) set.add(id);
    return [...set].sort((a, b) => a.localeCompare(b));
  }, [derived]);

  const colorOf = useMemo(() => {
    const map = new Map<string, string>();
    let i = 0;
    for (const id of ids) {
      map.set(id, PALETTE[i % PALETTE.length] ?? FALLBACK);
      i++;
    }
    return map;
  }, [ids]);

  const current = useMemo(() => {
    let last: InstanceRateRow | undefined;
    for (const row of derived) last = row;
    const rows = Object.entries(last?.rates ?? {})
      .map(([id, eps]) => ({ id, eps }))
      .sort((a, b) => b.eps - a.eps);
    const total = rows.reduce((sum, r) => sum + r.eps, 0);
    return { rows, total };
  }, [derived]);

  const data = useMemo(() => {
    const windowed = fixedWindow(derived, MAX_POINTS, { rates: {} });
    return windowed.map((p) => {
      const row: Record<string, number | string> = { time: p.time };
      for (const id of ids) row[id] = p.rates[id] ?? 0;
      return row;
    });
  }, [derived, ids]);

  const series = useMemo(
    () => ids.map((id) => ({ name: id, color: colorOf.get(id) ?? FALLBACK })),
    [ids, colorOf]
  );

  return (
    <Stack gap="xs">
      <SectionLabel>Instance load</SectionLabel>
      <Paper withBorder radius="md" p="md">
        {derived.length < 2 ? (
          <Center h={180}>
            <Text size="sm" c="dimmed">
              Collecting data...
            </Text>
          </Center>
        ) : (
          <Stack gap="sm">
            <Group gap="lg" wrap="wrap" justify="flex-end">
              <Metric
                value={`${formatEps(current.total)}/s`}
                label="total output"
              />
            </Group>
            <AreaChart
              h={180}
              data={data}
              dataKey="time"
              type="stacked"
              withXAxis={false}
              withYAxis
              withLegend={false}
              withDots={false}
              curveType="monotone"
              gridAxis="xy"
              fillOpacity={0.8}
              valueFormatter={(v) => `${formatEps(v)}/s`}
              xAxisProps={{ interval: 0 }}
              yAxisProps={{ width: 52 }}
              series={series}
            />
            <Group gap="md" wrap="wrap">
              {current.rows.map((r) => {
                const pct =
                  current.total > 0 ? (r.eps / current.total) * 100 : 0;
                return (
                  <Group key={r.id} gap={7} wrap="nowrap" align="center">
                    <Box
                      style={{
                        width: 10,
                        height: 10,
                        borderRadius: 3,
                        background: colorOf.get(r.id) ?? FALLBACK,
                        flexShrink: 0,
                      }}
                    />
                    <Text
                      size="sm"
                      fw={500}
                      style={{
                        maxWidth: 160,
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {r.id}
                    </Text>
                    <Text
                      size="sm"
                      ff="monospace"
                      fw={700}
                      style={{ fontVariantNumeric: 'tabular-nums' }}
                    >
                      {formatEps(r.eps)}/s
                    </Text>
                    <Text size="xs" c="dimmed">
                      {pct.toFixed(0)}%
                    </Text>
                  </Group>
                );
              })}
            </Group>
          </Stack>
        )}
      </Paper>
    </Stack>
  );
};
