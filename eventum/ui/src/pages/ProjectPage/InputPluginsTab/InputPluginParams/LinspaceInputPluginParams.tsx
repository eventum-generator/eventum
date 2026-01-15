import { Group, NumberInput, Stack, Switch, TagsInput } from '@mantine/core';
import { useForm } from '@mantine/form';
import { zod4Resolver } from 'mantine-form-zod-resolver';
import { FC } from 'react';

import { VersatileDatetimeInput } from '../../VersatileDatetimeInput';
import {
  LinspaceInputPluginConfig,
  LinspaceInputPluginConfigSchema,
} from '@/api/routes/generator-configs/schemas/plugins/input/configs/linspace';
import { LabelWithTooltip } from '@/components/ui/LabelWithTooltip';

interface LinspaceInputPluginParamsProps {
  initialConfig: LinspaceInputPluginConfig;
  onChange: (config: LinspaceInputPluginConfig) => void;
}

export const LinspaceInputPluginParams: FC<LinspaceInputPluginParamsProps> = ({
  initialConfig,
  onChange,
}) => {
  const form = useForm<LinspaceInputPluginConfig>({
    initialValues: initialConfig,
    onValuesChange: onChange,
    validate: zod4Resolver(LinspaceInputPluginConfigSchema),
    onSubmitPreventDefault: 'always',
    validateInputOnChange: true,
  });

  return (
    <Stack gap="xs">
      <Group grow align="start">
        <VersatileDatetimeInput
          label={
            <LabelWithTooltip
              label="Start time"
              tooltip="Start time of the generating date range."
            />
          }
          placeholder="time expression"
          required
          {...form.getInputProps('start')}
          value={form.getValues().start ?? ''}
          onChange={(value) =>
            form.setFieldValue(
              'start',
              value.currentTarget.value !== ''
                ? value.currentTarget.value
                : undefined!
            )
          }
        />
        <VersatileDatetimeInput
          label={
            <LabelWithTooltip
              label="End time"
              tooltip="End time of the generating date range."
            />
          }
          placeholder="time expression"
          required
          {...form.getInputProps('end')}
          value={form.getValues().end ?? ''}
          onChange={(value) =>
            form.setFieldValue(
              'end',
              value.currentTarget.value !== ''
                ? value.currentTarget.value
                : undefined!
            )
          }
        />
      </Group>

      <NumberInput
        label={
          <LabelWithTooltip
            label="Count"
            tooltip="Number of events within date range."
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

      <Switch
        label={
          <LabelWithTooltip
            label="Include end point"
            tooltip="Whether to include end point of date range."
          />
        }
        {...form.getInputProps('endpoint', { type: 'checkbox' })}
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
