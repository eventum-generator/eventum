import {
  Button,
  Group,
  NumberInput,
  SegmentedControl,
  Select,
  Stack,
  Switch,
  TextInput,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { notifications } from '@mantine/notifications';
import { FC, memo, useState } from 'react';

import { useProjectName } from '../../hooks/useProjectName';
import Visualization from './Visualization';
import { useGenerateTimestampsMutation } from '@/api/hooks/usePreview';
import { InputPluginsNamedConfig } from '@/api/routes/generator-configs/schemas';
import { TIMEZONES } from '@/api/schemas/timezones';
import { LabelWithTooltip } from '@/components/ui/LabelWithTooltip';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';

interface TimestampsHistogramProps {
  getSelectedPluginIndex: () => number;
  getInputPluginsConfig: () => InputPluginsNamedConfig;
}

type HistogramVisualizationMode = 'selectedPlugin' | 'allPlugins';

const VALID_SPAN_PATTERN = /^[-+]?(\d+d)?(\d+h)?(\d+m)?(\d+s)?$/;

const barColors = [
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

export type HistogramData = {
  timestamp: string;
  [group: string]: number | string;
}[];

export type HistogramSeries = {
  name: string;
  color: string;
}[];

const TimestampsHistogram: FC<TimestampsHistogramProps> = ({
  getSelectedPluginIndex,
  getInputPluginsConfig,
}) => {
  const { projectName } = useProjectName();
  const [visualizationMode, setVisualizationMode] =
    useState<HistogramVisualizationMode>('selectedPlugin');
  const [totalCount, setTotalCount] = useState(0);

  const generateTimestamp = useGenerateTimestampsMutation();

  const form = useForm<
    Omit<
      Parameters<ReturnType<typeof useGenerateTimestampsMutation>['mutate']>[0],
      'inputPluginsConfig' | 'name'
    >
  >({
    mode: 'uncontrolled',
    initialValues: {
      size: 100,
      span: null,
      timezone: 'UTC',
      skipPast: false,
    },
    transformValues: (values) => {
      if (values.span === '') {
        values.span = null;
      }

      return values;
    },
    validate: {
      span: (value) => {
        if (typeof value === 'string') {
          const isValid = VALID_SPAN_PATTERN.test(value);

          if (!isValid) {
            return 'Invalid span expression';
          }
        }

        return null;
      },
    },
    onSubmitPreventDefault: 'always',
    validateInputOnChange: true,
  });

  const [histogramData, setHistogramData] = useState<HistogramData>([]);
  const [histogramSeries, setHistogramSeries] = useState<HistogramSeries>([]);
  const [timestampsList, setTimestampsList] = useState('No timestamps');

  function handleGenerateTimestamp(values: typeof form.values) {
    let pluginsConfig = getInputPluginsConfig();

    if (visualizationMode !== 'allPlugins') {
      pluginsConfig = [pluginsConfig[getSelectedPluginIndex()]!];
    }

    generateTimestamp.mutate(
      {
        name: projectName,
        size: values.size,
        skipPast: values.skipPast,
        span: values.span,
        timezone: values.timezone,
        inputPluginsConfig: pluginsConfig,
      },
      {
        onSuccess: (value) => {
          const groups = Object.keys(value.span_counts);
          const groupNames = pluginsConfig.map((item, index, items) =>
            items.length > 1
              ? `${Object.keys(item)[0]!} #${index + 1}`
              : Object.keys(item)[0]!
          );

          const data: HistogramData = value.span_edges.map((edge, index) => {
            const row: HistogramData[number] = {
              timestamp: edge,
            };

            for (const group of groups) {
              row[groupNames[Number(group) - 1]!] =
                value.span_counts[group]?.[index] ?? 0;
            }

            return row;
          });

          setHistogramData(data);

          setHistogramSeries(
            groupNames.map((groupName, i) => ({
              name: groupName,
              color: barColors[i % barColors.length]!,
            }))
          );

          setTotalCount(value.total);

          setTimestampsList(
            value.timestamps === null
              ? JSON.stringify(
                  [
                    ...(value.first_timestamps ?? []),
                    `... (${value.total - (value.first_timestamps?.length ?? 0) - (value.last_timestamps?.length ?? 0)} lines skipped)`,
                    ...(value.last_timestamps ?? []),
                  ],
                  undefined,
                  2
                )
              : JSON.stringify(value.timestamps, undefined, 2)
          );
        },
        onError: (error) => {
          notifications.show({
            title: 'Error',
            message: (
              <>
                Failed to generate timestamps.{' '}
                <ShowErrorDetailsAnchor error={error} />
              </>
            ),
            color: 'red',
          });
        },
      }
    );
  }

  return (
    <Stack gap="xs">
      <form onSubmit={form.onSubmit(handleGenerateTimestamp)}>
        <Stack gap="xs">
          <Group grow align="start" h="65px">
            <NumberInput
              min={1}
              allowDecimal={false}
              label={
                <LabelWithTooltip
                  label="Number of timestamps"
                  tooltip="Limit of generated timestamps that are shown on histogram"
                />
              }
              {...form.getInputProps('size', { type: 'input' })}
            />
            <TextInput
              label={
                <LabelWithTooltip
                  label="Time span"
                  tooltip="Duration of each histogram bin, default is auto calculated"
                />
              }
              placeholder="span (e.g. 30s, 5m, 1h)"
              {...form.getInputProps('span', { type: 'input' })}
            />
            <Select
              label={
                <LabelWithTooltip
                  label="Timezone"
                  tooltip="Timezone that will be used in normalized datetime"
                />
              }
              data={TIMEZONES}
              searchable
              nothingFoundMessage="No timezones matched"
              placeholder="zone name"
              {...form.getInputProps('timezone', { type: 'input' })}
            />
          </Group>

          <Group justify="space-between">
            <Group>
              <SegmentedControl
                value={visualizationMode}
                onChange={setVisualizationMode as (value: string) => void}
                data={[
                  { label: 'Selected plugin', value: 'selectedPlugin' },
                  { label: 'All plugins', value: 'allPlugins' },
                ]}
              />

              <Switch
                label={
                  <LabelWithTooltip
                    label="Skip past timestamps"
                    tooltip="Start histogram from first non past timestamp"
                  />
                }
                {...form.getInputProps('skipPast', { type: 'checkbox' })}
              />
            </Group>
            <Button
              variant="default"
              type="submit"
              loading={generateTimestamp.isPending}
            >
              Generate
            </Button>
          </Group>
        </Stack>
      </form>

      <Visualization
        histogramData={histogramData}
        histogramSeries={histogramSeries}
        totalCount={totalCount}
        timestampsList={timestampsList}
      />
    </Stack>
  );
};

export default memo(TimestampsHistogram);
