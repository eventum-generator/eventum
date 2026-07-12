import { AreaChart } from '@mantine/charts';
import { Center, Group, Paper, Stack, Text } from '@mantine/core';
import { FC, useMemo } from 'react';

import { Metric } from './Metric';
import { SectionLabel } from './SectionLabel';
import {
  ErrorDatum,
  FlowPoint,
  MAX_POINTS,
  errorData,
  fixedWindow,
} from './history';

const BAD = 'var(--ev-bad)';
const WARN = 'var(--ev-warn)';

export const ErrorsChart: FC<{ flow: FlowPoint[] }> = ({ flow }) => {
  const real = useMemo(() => errorData(flow), [flow]);
  const data = useMemo(
    () => fixedWindow(real, MAX_POINTS, { event: null, output: null }),
    [real]
  );
  let last: ErrorDatum | undefined;
  for (const row of real) last = row;
  const eventNow = last?.event ?? 0;
  const outputNow = last?.output ?? 0;

  return (
    <Stack gap="xs">
      <SectionLabel>Failures</SectionLabel>
      <Paper withBorder radius="md" p="md">
        {real.length < 2 ? (
          <Center h={150}>
            <Text size="sm" c="dimmed">
              Collecting data...
            </Text>
          </Center>
        ) : (
          <Stack gap="sm">
            <Group gap="lg" wrap="wrap" justify="flex-end">
              <Metric
                value={`${eventNow.toFixed(2)}/s`}
                label="event"
                color={BAD}
              />
              <Metric
                value={`${outputNow.toFixed(2)}/s`}
                label="output"
                color={WARN}
              />
            </Group>
            <AreaChart
              h={150}
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
              valueFormatter={(v) => `${v.toFixed(2)}/s`}
              xAxisProps={{ interval: 0 }}
              yAxisProps={{ width: 52 }}
              series={[
                { name: 'event', label: 'Event', color: BAD },
                { name: 'output', label: 'Output', color: WARN },
              ]}
            />
          </Stack>
        )}
      </Paper>
    </Stack>
  );
};
