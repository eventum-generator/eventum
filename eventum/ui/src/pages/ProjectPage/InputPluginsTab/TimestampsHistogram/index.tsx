import { CodeHighlight } from '@mantine/code-highlight';
import {
  Badge,
  Button,
  Input,
  MultiSelect,
  NumberInput,
  Select,
  Switch,
  TextInput,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { notifications } from '@mantine/notifications';
import { IconChartHistogram } from '@tabler/icons-react';
import { FC, memo, useState } from 'react';

import { useProjectName } from '../../hooks/useProjectName';
import {
  ToolBody,
  ToolEmpty,
  ToolPane,
  ToolShell,
  ToolSpacer,
} from '../../studio/panels/console/primitives';
import Visualization from './Visualization';
import { useGenerateTimestampsMutation } from '@/api/hooks/usePreview';
import { InputPluginsNamedConfig } from '@/api/routes/generator-configs/schemas';
import { TIMEZONES } from '@/api/schemas/timezones';
import { LabelWithTooltip } from '@/components/ui/LabelWithTooltip';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';

interface TimestampsHistogramProps {
  pluginNames: string[];
  getInputPluginsConfig: () => InputPluginsNamedConfig;
}

const VALID_SPAN_PATTERN = /^[-+]?(\d+d)?(\d+h)?(\d+m)?(\d+s)?$/;

/* eslint-disable no-restricted-syntax -- categorical histogram palette needs distinct swatches beyond the token set */
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
/* eslint-enable no-restricted-syntax */

export type HistogramData = {
  timestamp: string;
  [group: string]: number | string;
}[];

export type HistogramSeries = {
  name: string;
  color: string;
}[];

/** Labels a list of plugin names, disambiguating repeats of the same type
 *  with a per-name occurrence number (`timer #1`, `timer #2`); a type that
 *  appears once keeps its plain name. */
function labelNames(names: string[]): string[] {
  const seen: Record<string, number> = {};
  return names.map((name) => {
    const total = names.filter((other) => other === name).length;
    seen[name] = (seen[name] ?? 0) + 1;
    return total > 1 ? `${name} #${seen[name]}` : name;
  });
}

const TimestampsHistogram: FC<TimestampsHistogramProps> = ({
  pluginNames,
  getInputPluginsConfig,
}) => {
  const { projectName } = useProjectName();
  // Empty selection means "all plugins" - one control covers both the
  // multi-select and the all case.
  const [selected, setSelected] = useState<string[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [hasRun, setHasRun] = useState(false);

  const generateTimestamp = useGenerateTimestampsMutation();

  const pluginOptions = labelNames(pluginNames).map((label, index) => ({
    value: String(index),
    label,
  }));

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
    const allConfigs = getInputPluginsConfig();

    let pluginsConfig = allConfigs;
    if (selected.length > 0) {
      const subset = selected
        .map((index) => allConfigs[Number(index)])
        .filter((config) => config !== undefined);

      if (subset.length > 0) {
        pluginsConfig = subset;
      }
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
          const groupNames = labelNames(
            pluginsConfig.map((item) => Object.keys(item)[0]!)
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

          setHasRun(true);
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
    <form
      onSubmit={form.onSubmit(handleGenerateTimestamp)}
      style={{ display: 'contents' }}
    >
      <ToolShell
        toolbar={
          <>
            <MultiSelect
              size="xs"
              w={260}
              label={
                <LabelWithTooltip
                  label="Plugins"
                  tooltip="Input plugins to generate timestamps for. Leave empty to include all; select several to combine them."
                />
              }
              data={pluginOptions}
              value={selected}
              onChange={setSelected}
              placeholder={selected.length === 0 ? 'All plugins' : ''}
              clearable
              searchable
              hidePickedOptions
              styles={{ input: { maxHeight: 92, overflowY: 'auto' } }}
            />
            <NumberInput
              size="xs"
              w={100}
              min={1}
              allowDecimal={false}
              label={
                <LabelWithTooltip
                  label="Count"
                  tooltip="Limit of generated timestamps that are shown on histogram"
                />
              }
              {...form.getInputProps('size', { type: 'input' })}
            />
            <TextInput
              size="xs"
              w={130}
              label={
                <LabelWithTooltip
                  label="Time span"
                  tooltip="Duration of each histogram bin, default is auto calculated"
                />
              }
              placeholder="auto (30s, 5m)"
              {...form.getInputProps('span', { type: 'input' })}
            />
            <Select
              size="xs"
              w={140}
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
            <Input.Wrapper
              size="xs"
              label={
                <LabelWithTooltip
                  label="Skip past"
                  tooltip="Start histogram from first non past timestamp"
                />
              }
            >
              <div className="tool-switch-slot">
                <Switch
                  size="xs"
                  {...form.getInputProps('skipPast', { type: 'checkbox' })}
                />
              </div>
            </Input.Wrapper>
            <ToolSpacer />
            <Button
              size="xs"
              className="tool-ctl"
              type="submit"
              loading={generateTimestamp.isPending}
            >
              Generate
            </Button>
          </>
        }
      >
        {hasRun ? (
          <ToolBody>
            <ToolPane
              title="Distribution"
              grow={3}
              fill
              actions={
                <Badge variant="light" size="sm">
                  {totalCount} total
                </Badge>
              }
            >
              <div className="tool-chart">
                <Visualization
                  histogramData={histogramData}
                  histogramSeries={histogramSeries}
                />
              </div>
            </ToolPane>
            <ToolPane title="Timestamps" grow={1}>
              <CodeHighlight
                code={timestampsList}
                language="json"
                withCopyButton
              />
            </ToolPane>
          </ToolBody>
        ) : (
          <ToolBody empty>
            <ToolEmpty icon={<IconChartHistogram size={28} />}>
              Configure the parameters and run to preview the timestamp
              distribution and the generated timestamps.
            </ToolEmpty>
          </ToolBody>
        )}
      </ToolShell>
    </form>
  );
};

export default memo(TimestampsHistogram);
