import { BarChart } from '@mantine/charts';
import { FC, memo } from 'react';

import { HistogramData, HistogramSeries } from '.';

interface VisualizationProps {
  histogramData: HistogramData;
  histogramSeries: HistogramSeries;
}

const Visualization: FC<VisualizationProps> = ({
  histogramData,
  histogramSeries,
}) => {
  return (
    <BarChart
      h="100%"
      w="100%"
      data={histogramData}
      dataKey="timestamp"
      type="stacked"
      series={histogramSeries}
      xAxisLabel="Time"
      yAxisLabel="Count"
      withLegend
    />
  );
};

export default memo(Visualization);
