import {
  Group,
  NumberInput,
  Stack,
  TagsInput,
  Text,
  TextInput,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import cronstrue from 'cronstrue';
import { zod4Resolver } from 'mantine-form-zod-resolver';
import { FC } from 'react';
import z from 'zod';

import { VersatileDatetimeInput } from '../../VersatileDatetimeInput';
import {
  CronInputPluginConfig,
  CronInputPluginConfigSchema,
} from '@/api/routes/generator-configs/schemas/plugins/input/configs/cron';
import { LabelWithTooltip } from '@/components/ui/LabelWithTooltip';

interface CronInputPluginParamsProps {
  initialConfig: CronInputPluginConfig;
  onChange: (config: CronInputPluginConfig) => void;
}

const CronExpressionSchema = z.string().refine(
  (value) => {
    try {
      cronstrue.toString(value);
      return true;
    } catch {
      return false;
    }
  },
  { message: 'Invalid cron expression' }
);

const ExtendedCronInputPluginConfigSchema = CronInputPluginConfigSchema.extend({
  expression: CronExpressionSchema,
});

export const CronInputPluginParams: FC<CronInputPluginParamsProps> = ({
  initialConfig,
  onChange,
}) => {
  const form = useForm<CronInputPluginConfig>({
    initialValues: initialConfig,
    onValuesChange: onChange,
    validate: zod4Resolver(ExtendedCronInputPluginConfigSchema),
    onSubmitPreventDefault: 'always',
    validateInputOnChange: true,
  });

  let cronDescription = '';
  try {
    cronDescription = cronstrue.toString(form.values.expression);
  } catch {
    /* empty */
  }

  return (
    <Stack gap="xs">
      <Group grow align="start">
        <Stack gap="5px">
          <TextInput
            label={
              <LabelWithTooltip
                label="Expression"
                tooltip="Cron expression (supports specifying seconds, years, random
        values and keywords)"
              />
            }
            required
            placeholder="cron expression"
            {...form.getInputProps('expression')}
          />
          <Text size="xs" c="gray.6">
            {cronDescription}
          </Text>
        </Stack>
        <NumberInput
          label={
            <LabelWithTooltip
              label="Count"
              tooltip="Number of timestamps to generate for every cron interval"
            />
          }
          required
          min={1}
          step={1}
          allowDecimal={false}
          {...form.getInputProps('count')}
          value={form.getValues().count ?? ''}
          onChange={(value) =>
            form.setFieldValue(
              'count',
              typeof value === 'number' ? value : undefined!
            )
          }
        />
      </Group>
      <Group grow align="start">
        <VersatileDatetimeInput
          label={
            <LabelWithTooltip
              label="Start time"
              tooltip="Start of the generating date range, if not set, current time is used"
            />
          }
          placeholder="time expression"
          {...form.getInputProps('start')}
          onChange={(value) =>
            form.setFieldValue(
              'start',
              value.currentTarget.value !== ''
                ? value.currentTarget.value
                : undefined
            )
          }
        />
        <VersatileDatetimeInput
          label={
            <LabelWithTooltip
              label="End time"
              tooltip="End time of the generating date range, if not set, then never end generation."
            />
          }
          placeholder="time expression"
          {...form.getInputProps('end')}
          onChange={(value) =>
            form.setFieldValue(
              'end',
              value.currentTarget.value !== ''
                ? value.currentTarget.value
                : undefined
            )
          }
        />
      </Group>
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
