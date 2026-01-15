import { Group, NumberInput, Stack, TagsInput } from '@mantine/core';
import { useForm } from '@mantine/form';
import { zod4Resolver } from 'mantine-form-zod-resolver';
import { FC } from 'react';

import {
  TimerInputPluginConfig,
  TimerInputPluginConfigSchema,
} from '@/api/routes/generator-configs/schemas/plugins/input/configs/timer';
import { LabelWithTooltip } from '@/components/ui/LabelWithTooltip';
import { VersatileDatetimeInput } from '@/pages/ProjectPage/VersatileDatetimeInput';

interface TimerInputPluginParamsProps {
  initialConfig: TimerInputPluginConfig;
  onChange: (config: TimerInputPluginConfig) => void;
}

export const TimerInputPluginParams: FC<TimerInputPluginParamsProps> = ({
  initialConfig,
  onChange,
}) => {
  const form = useForm<TimerInputPluginConfig>({
    initialValues: initialConfig,
    onValuesChange: onChange,
    validate: zod4Resolver(TimerInputPluginConfigSchema),
    validateInputOnChange: true,
    onSubmitPreventDefault: 'always',
  });

  return (
    <Stack gap="xs">
      <Group grow align="start">
        <NumberInput
          label={
            <LabelWithTooltip
              label="Seconds"
              tooltip="Number of seconds to wait before generating timestamp"
            />
          }
          suffix=" s."
          min={0.1}
          step={1}
          required
          {...form.getInputProps('seconds')}
          value={form.getValues().seconds ?? ''}
          onChange={(value) =>
            form.setFieldValue(
              'seconds',
              typeof value === 'number' ? value : undefined!
            )
          }
        />
        <NumberInput
          label={
            <LabelWithTooltip
              label="Count"
              tooltip="Number of timestamps to generate"
            />
          }
          min={1}
          step={1}
          allowDecimal={false}
          required
          {...form.getInputProps('count')}
          value={form.getValues().count ?? ''}
          onChange={(value) =>
            form.setFieldValue(
              'count',
              typeof value === 'number' ? value : undefined!
            )
          }
        />
        <NumberInput
          min={1}
          allowDecimal={false}
          label={
            <LabelWithTooltip
              label="Repeat"
              tooltip="Number of cycles to repeat, if value is not set, then repeat infinitely"
            />
          }
          placeholder="infinitely"
          suffix=" times"
          {...form.getInputProps('repeat')}
          value={form.getValues().repeat ?? ''}
          onChange={(value) =>
            form.setFieldValue(
              'repeat',
              typeof value === 'number' ? value : undefined
            )
          }
        />
      </Group>

      <VersatileDatetimeInput
        label={
          <LabelWithTooltip
            label="Start time"
            tooltip="Start time of timer countdown, if not set current time is used"
          />
        }
        placeholder="time expression"
        {...form.getInputProps('start')}
        value={form.getValues().start ?? ''}
        onChange={(value) =>
          form.setFieldValue(
            'start',
            value.currentTarget.value !== ''
              ? value.currentTarget.value
              : undefined
          )
        }
      />
      <TagsInput
        label={
          <LabelWithTooltip
            label="Tags"
            tooltip="Tags list attached to an input plugin"
          />
        }
        placeholder="Press Enter to submit a tag"
        {...form.getInputProps('tags')}
        value={form.getValues().tags ?? []}
        onChange={(value) =>
          form.setFieldValue('tags', value.length > 0 ? value : undefined)
        }
      />
    </Stack>
  );
};
