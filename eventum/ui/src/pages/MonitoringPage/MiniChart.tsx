import { AreaChart } from '@mantine/charts';
import { Center, Text } from '@mantine/core';

import { MAX_POINTS, fixedWindow } from './history';

interface MiniSeries<T> {
  key: keyof T & string;
  name: string;
  color: string;
}

interface MiniChartProps<T extends { t: number; time: string }> {
  data: T[];
  series: MiniSeries<T>[];
  valueFormatter: (value: number) => string;
  tickFormatter?: (value: number) => string;
  domain?: [number, number];
  ticks?: number[];
  h?: number | string;
  /** Length of the drawn window in points; the page-wide selector sets it. */
  points?: number;
}

export function MiniChart<T extends { t: number; time: string }>({
  data,
  series,
  valueFormatter,
  tickFormatter,
  domain,
  ticks,
  h = '100%',
  points = MAX_POINTS,
}: Readonly<MiniChartProps<T>>) {
  if (data.length < 2) {
    return (
      <Center h={h}>
        <Text size="sm" c="dimmed">
          Collecting data...
        </Text>
      </Center>
    );
  }

  const empty = Object.fromEntries(series.map((s) => [s.key, null])) as Omit<
    T,
    't' | 'time'
  >;
  const windowed = fixedWindow(data, points, empty);

  return (
    <AreaChart
      h={h}
      data={windowed}
      dataKey="time"
      series={series.map((s) => ({
        name: s.key,
        label: s.name,
        color: s.color,
      }))}
      withXAxis={false}
      withYAxis
      xAxisProps={{ interval: 0 }}
      yAxisProps={{
        width: 56,
        domain: domain ?? ['auto', 'auto'],
        tickFormatter: tickFormatter ?? valueFormatter,
        ...(ticks ? { ticks } : { tickCount: 4 }),
      }}
      valueFormatter={valueFormatter}
      withDots={false}
      connectNulls={false}
      curveType="monotone"
      gridAxis="xy"
      fillOpacity={0.1}
      strokeWidth={1.75}
      withTooltip
    />
  );
}
