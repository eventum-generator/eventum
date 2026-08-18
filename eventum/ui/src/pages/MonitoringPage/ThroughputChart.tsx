import { AreaChart } from '@mantine/charts';
import { Center, Group, Paper, Stack, Text } from '@mantine/core';
import { FC, useMemo } from 'react';

import { Metric } from './Metric';
import { SectionLabel } from './SectionLabel';
import { ACCENT, CYAN } from './colors';
import { formatAxis, formatEps } from './format';
import { FlowPoint, MAX_POINTS, fixedWindow, throughputData } from './history';

interface ThroughputChartProps {
  flow: FlowPoint[];
  inputEps: number;
  outputEps: number;
  /** Length of the drawn window in points; the page-wide selector sets it. */
  points?: number;
  height?: number;
}

export const ThroughputChart: FC<ThroughputChartProps> = ({
  flow,
  inputEps,
  outputEps,
  points = MAX_POINTS,
  height = 160,
}) => {
  const real = useMemo(() => throughputData(flow), [flow]);
  const data = useMemo(
    () => fixedWindow(real, points, { input: null, output: null }),
    [real, points]
  );
  return (
    <Stack gap="xs">
      <SectionLabel>Throughput</SectionLabel>
      <Paper withBorder p="md">
        {real.length < 2 ? (
          <Center h={height}>
            <Text size="sm" c="dimmed">
              Collecting data...
            </Text>
          </Center>
        ) : (
          <Stack gap="sm">
            <Group gap="lg" wrap="wrap" justify="flex-end">
              <Metric
                value={`${formatEps(inputEps)}/s`}
                label="input"
                color={CYAN}
              />
              <Metric
                value={`${formatEps(outputEps)}/s`}
                label="output"
                color={ACCENT}
              />
            </Group>
            <AreaChart
              h={height}
              data={data}
              dataKey="time"
              withXAxis={false}
              withYAxis
              withLegend={false}
              withDots={false}
              connectNulls={false}
              curveType="monotone"
              gridAxis="xy"
              fillOpacity={0.15}
              valueFormatter={(v) => `${formatEps(v)}/s`}
              xAxisProps={{ interval: 0 }}
              yAxisProps={{ width: 56, tickFormatter: formatAxis }}
              series={[
                { name: 'input', label: 'Input', color: CYAN },
                { name: 'output', label: 'Output', color: ACCENT },
              ]}
            />
          </Stack>
        )}
      </Paper>
    </Stack>
  );
};
