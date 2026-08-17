import { AreaChart } from '@mantine/charts';
import { Box, Center, Group, Text, UnstyledButton } from '@mantine/core';
import { FC, useMemo } from 'react';

import { ACCENT, CYAN } from './colors';
import { formatAxis, formatEps } from './format';
import { FlowPoint, InstanceRateRow, fixedWindow, stageData } from './history';
import { FALLBACK_COLOR } from './instanceColors';

const MUTED = 'var(--mantine-color-default-border)';
const EVENT_COLOR = 'var(--mantine-color-green-text)';
const HEIGHT = 200;

interface LoadChartProps {
  /** Per-instance bands, already ranked and folded to a readable count. */
  bands: InstanceRateRow[];
  bandIds: string[];
  colorOf: Map<string, string>;
  flow: FlowPoint[];
  groupBy: 'instance' | 'stage';
  points: number;
  selectedId: string | null;
  onSelect: (id: string | null) => void;
}

/**
 * The output load of the fleet over the window, split either by instance or
 * by pipeline stage. Split by instance the bands stack into the total, so the
 * share of each instance is the height of its band; split by stage the three
 * lines show where the pipeline narrows - events produced below timestamps
 * generated means the event stage is behind, events written below produced
 * means the destinations are.
 *
 * Colours are keyed to instance id and shared with the table below, and the
 * selection is shared as well: selecting an instance keeps its band in colour
 * and mutes the rest.
 */
export const LoadChart: FC<LoadChartProps> = ({
  bands,
  bandIds,
  colorOf,
  flow,
  groupBy,
  points,
  selectedId,
  onSelect,
}) => {
  const instanceData = useMemo(() => {
    const windowed = fixedWindow(bands, points, { rates: {} });
    return windowed.map((row) => {
      const point: Record<string, number | string> = { time: row.time };
      for (const id of bandIds) point[id] = row.rates[id] ?? 0;
      return point;
    });
  }, [bands, bandIds, points]);

  const stagePoints = useMemo(() => stageData(flow), [flow]);
  const stageWindow = useMemo(
    () =>
      fixedWindow(stagePoints, points, {
        input: null,
        event: null,
        output: null,
      }),
    [stagePoints, points]
  );

  const current = useMemo(() => {
    let last: InstanceRateRow | undefined;
    for (const row of bands) last = row;
    const rows = Object.entries(last?.rates ?? {})
      .map(([id, eps]) => ({ id, eps }))
      .sort((a, b) => b.eps - a.eps);
    return { rows, total: rows.reduce((sum, row) => sum + row.eps, 0) };
  }, [bands]);

  const series = useMemo(
    () =>
      bandIds.map((id) => ({
        name: id,
        color:
          selectedId && id !== selectedId
            ? MUTED
            : (colorOf.get(id) ?? FALLBACK_COLOR),
      })),
    [bandIds, colorOf, selectedId]
  );

  const enough =
    groupBy === 'instance' ? bands.length > 1 : stagePoints.length > 1;
  if (!enough) {
    return (
      <Center h={HEIGHT}>
        <Text size="sm" c="dimmed">
          Collecting data...
        </Text>
      </Center>
    );
  }

  if (groupBy === 'stage') {
    return (
      <AreaChart
        h={HEIGHT}
        data={stageWindow}
        dataKey="time"
        withXAxis={false}
        withYAxis
        withLegend
        withDots={false}
        connectNulls={false}
        curveType="monotone"
        gridAxis="xy"
        fillOpacity={0.12}
        valueFormatter={(v) => `${formatEps(v)}/s`}
        xAxisProps={{ interval: 0 }}
        yAxisProps={{ width: 56, tickFormatter: formatAxis }}
        series={[
          { name: 'input', label: 'Timestamps', color: CYAN },
          { name: 'event', label: 'Produced', color: EVENT_COLOR },
          { name: 'output', label: 'Written', color: ACCENT },
        ]}
      />
    );
  }

  return (
    <>
      <AreaChart
        h={HEIGHT}
        data={instanceData}
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
        yAxisProps={{ width: 56, tickFormatter: formatAxis }}
        series={series}
      />
      <Group gap="md" wrap="wrap">
        {current.rows.map((row) => {
          const share = current.total > 0 ? (row.eps / current.total) * 100 : 0;
          const dimmed = selectedId !== null && selectedId !== row.id;
          return (
            <UnstyledButton
              key={row.id}
              onClick={() => onSelect(selectedId === row.id ? null : row.id)}
              style={{ opacity: dimmed ? 0.45 : 1 }}
            >
              <Group gap={7} wrap="nowrap" align="center">
                <Box
                  style={{
                    width: 10,
                    height: 10,
                    borderRadius: 3,
                    background: colorOf.get(row.id) ?? FALLBACK_COLOR,
                    flexShrink: 0,
                  }}
                />
                <Text size="sm" fw={500} truncate maw={160}>
                  {row.id}
                </Text>
                <Text
                  size="sm"
                  ff="monospace"
                  fw={700}
                  style={{ fontVariantNumeric: 'tabular-nums' }}
                >
                  {formatEps(row.eps)}/s
                </Text>
                <Text size="xs" c="dimmed">
                  {share.toFixed(0)}%
                </Text>
              </Group>
            </UnstyledButton>
          );
        })}
      </Group>
    </>
  );
};
