import { BarChart, PieChart } from '@mantine/charts';
import { Grid, Group, Paper, Stack, Text, Title } from '@mantine/core';
import { FC, ReactNode } from 'react';
import { ResponsiveContainer } from 'recharts';

import { GeneratorStats } from '@/api/routes/generators/schemas';
import { LabelWithTooltip } from '@/components/ui/LabelWithTooltip';

const pieColors = [
  '#8282ef',
  '#32d3c8',
  '#9cc94c',
  '#f5a042',
  '#e16aa5',
  '#8792ff',
  '#50c1a4',

  '#6e9bff',
  '#3fc48c',
  '#d6c83c',
  '#f38355',
  '#d47adf',
  '#7da2e0',
  '#5da86f',

  '#4cc3ff',
  '#6dc061',
  '#f2c04a',
  '#e66a71',
  '#b889ff',
  '#66b7d5',
  '#49a07c',
];

interface InstancesStatsPanelProps {
  generatorsStats: GeneratorStats[];
}

export const InstancesStatsPanel: FC<InstancesStatsPanelProps> = ({
  generatorsStats,
}) => {
  const totalMetrics = generatorsStats
    .map((stats) => ({
      id: stats.id,
      generated: stats.total_generated,
      produced: stats.event.produced,
      written: stats.total_written,
      inputEPS: stats.input_eps,
      outputEPS: stats.output_eps,
    }))
    .sort((a, b) => b.produced - a.produced);

  // eslint-disable-next-line unicorn/no-array-reduce
  const totalAggregatedMetrics = totalMetrics.reduce(
    (prev, curr) => ({
      id: '',
      generated: prev.generated + curr.generated,
      produced: prev.produced + curr.produced,
      written: prev.written + curr.written,
      inputEPS: prev.inputEPS + curr.inputEPS,
      outputEPS: prev.outputEPS + curr.outputEPS,
    }),
    {
      id: '',
      generated: 0,
      produced: 0,
      written: 0,
      inputEPS: 0,
      outputEPS: 0,
    }
  );

  const totalMetricsItems: { content: ReactNode; caption: ReactNode }[] = [
    {
      content: totalAggregatedMetrics.generated,
      caption: (
        <LabelWithTooltip
          label="Generated"
          tooltip="Number of timestamps produced by input plugins of all active instances"
        />
      ),
    },
    {
      content: totalAggregatedMetrics.produced,
      caption: (
        <LabelWithTooltip
          label="Produced"
          tooltip="Number of events produced by event plugins of all active instances "
        />
      ),
    },
    {
      content: totalAggregatedMetrics.written,
      caption: (
        <LabelWithTooltip
          label="Written"
          tooltip="Number of events written by all output plugins of all active instances"
        />
      ),
    },
  ];

  const epsMetricsItems: { content: ReactNode; caption: ReactNode }[] = [
    {
      content: totalAggregatedMetrics.inputEPS.toFixed(2),
      caption: 'Input EPS',
    },
    {
      content: totalAggregatedMetrics.outputEPS.toFixed(2),
      caption: 'Output EPS',
    },
  ];

  return (
    <Paper withBorder p="md">
      <Stack gap="xs">
        <Title order={4} fw="500">
          Flow stats
        </Title>

        <Grid columns={12}>
          <Grid.Col span={8}>
            <Paper withBorder p="sm">
              <Group grow justify="space-between">
                {totalMetricsItems.map((metric, index) => (
                  <Stack key={index} gap="2px" align="center">
                    <Title order={2} fw="500">
                      {metric.content}
                    </Title>
                    <Text size="sm" ml="10px">
                      {metric.caption}
                    </Text>
                  </Stack>
                ))}
              </Group>
            </Paper>
          </Grid.Col>

          <Grid.Col span={4}>
            <Paper withBorder p="sm">
              <Group grow justify="space-between">
                {epsMetricsItems.map((metric, index) => (
                  <Stack key={index} gap="2px" align="center">
                    <Title order={2} fw="500">
                      {metric.content}
                    </Title>
                    <Text size="sm">{metric.caption}</Text>
                  </Stack>
                ))}
              </Group>
            </Paper>
          </Grid.Col>
        </Grid>

        <Grid columns={12} mt="xs">
          <Grid.Col span={8}>
            <Stack gap="xs">
              <Text size="sm" mb="xs">
                Instances by produced events
              </Text>

              {totalMetrics.length === 0 && (
                <Text c="gray.6" size="sm" ta="center" mt="xl">
                  No data
                </Text>
              )}

              {totalMetrics.length > 0 && (
                <ResponsiveContainer width="100%" height={150}>
                  <BarChart
                    data={totalMetrics}
                    dataKey="id"
                    series={[{ name: 'produced', color: 'primary' }]}
                    h="100%"
                    w="100%"
                    withXAxis={false}
                  />
                </ResponsiveContainer>
              )}
            </Stack>
          </Grid.Col>

          <Grid.Col span={4}>
            <Stack gap="xs">
              <Text size="sm" mb="xs" ta="center">
                Instances by output EPS
              </Text>

              {totalMetrics.length === 0 && (
                <Text c="gray.6" size="sm" ta="center" my="xl">
                  No data
                </Text>
              )}

              {totalMetrics.length > 0 && (
                <ResponsiveContainer width="100%" height={150}>
                  <PieChart
                    data={totalMetrics.map((item, index) => ({
                      name: item.id,
                      value: item.outputEPS,
                      color: pieColors[index % pieColors.length]!,
                    }))}
                    h="150"
                    w="150"
                    size={150}
                    withTooltip
                    tooltipDataSource="segment"
                    startAngle={90}
                    endAngle={-270}
                    valueFormatter={(value) => value.toFixed(2)}
                  />
                </ResponsiveContainer>
              )}
            </Stack>
          </Grid.Col>
        </Grid>
      </Stack>
    </Paper>
  );
};
