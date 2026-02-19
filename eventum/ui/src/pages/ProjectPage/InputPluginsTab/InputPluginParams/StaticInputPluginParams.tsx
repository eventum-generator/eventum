import { NumberInput, Stack, TagsInput } from '@mantine/core';
import { useForm } from '@mantine/form';
import { zod4Resolver } from 'mantine-form-zod-resolver';
import { FC } from 'react';

import {
  StaticInputPluginConfig,
  StaticInputPluginConfigSchema,
} from '@/api/routes/generator-configs/schemas/plugins/input/configs/static';
import { LabelWithTooltip } from '@/components/ui/LabelWithTooltip';

interface StaticInputPluginParamsProps {
  initialConfig: StaticInputPluginConfig;
  onChange: (config: StaticInputPluginConfig) => void;
}

export const StaticInputPluginParams: FC<StaticInputPluginParamsProps> = ({
  initialConfig,
  onChange,
}) => {
  const form = useForm<StaticInputPluginConfig>({
    initialValues: initialConfig,
    onValuesChange: onChange,
    validate: zod4Resolver(StaticInputPluginConfigSchema),
    onSubmitPreventDefault: 'always',
    validateInputOnChange: true,
  });

  return (
    <Stack gap="xs">
      <NumberInput
        label={
          <LabelWithTooltip
            label="Count"
            tooltip="Number of events to generate."
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
