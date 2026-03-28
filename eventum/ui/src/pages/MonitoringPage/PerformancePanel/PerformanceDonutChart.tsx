import { DonutChart, DonutChartCell } from '@mantine/charts';
import { Group } from '@mantine/core';
import { FC, ReactNode } from 'react';
import { ResponsiveContainer } from 'recharts';

interface PerformanceDonutChartProps {
  data: DonutChartCell[];
  chartLabel?: string;
  valueFormatter?: (value: number) => string;
  rightSection?: ReactNode;
}

export const PerformanceDonutChart: FC<PerformanceDonutChartProps> = ({
  data,
  chartLabel,
  valueFormatter,
  rightSection,
}) => {
  return (
    <Group wrap="nowrap" gap="xs" justify="center">
      <ResponsiveContainer width={80} height={80}>
        <DonutChart
          data={data}
          h="80"
          w="80"
          chartLabel={chartLabel}
          tooltipDataSource="segment"
          startAngle={90}
          endAngle={-270}
          size={80}
          thickness={10}
          valueFormatter={valueFormatter}
        />
      </ResponsiveContainer>
      {rightSection}
    </Group>
  );
};
