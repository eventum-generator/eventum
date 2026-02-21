import { JsonInput, Paper, Stack } from '@mantine/core';
import { useForm } from '@mantine/form';
import { zod4Resolver } from 'mantine-form-zod-resolver';
import { FC } from 'react';

import { SamplesSection } from './SamplesSection';
import { TemplatesSection } from './TemplatesSection';
import {
  TemplateEventPluginConfig,
  TemplateEventPluginConfigSchema,
} from '@/api/routes/generator-configs/schemas/plugins/event/configs/template';

interface TemplateEventPluginParamsProps {
  initialConfig: TemplateEventPluginConfig;
  onChange: (config: TemplateEventPluginConfig) => void;
}

export const TemplateEventPluginParams: FC<TemplateEventPluginParamsProps> = ({
  initialConfig,
  onChange,
}) => {
  const form = useForm<TemplateEventPluginConfig>({
    initialValues: initialConfig,
    validate: zod4Resolver(TemplateEventPluginConfigSchema),
    onValuesChange: onChange,
    onSubmitPreventDefault: 'always',
    validateInputOnChange: true,
  });

  return (
    <Stack gap="xs">
      <JsonInput
        label="Parameters"
        description="Each parameter is an attribute of a single JSON object"
        placeholder="{ ... }"
        validationError="Invalid JSON"
        minRows={4}
        autosize
        defaultValue={JSON.stringify(form.getValues().params, undefined, 2)}
        onChange={(value) => {
          if (!value) {
            form.setFieldValue('params', undefined);
            return;
          }

          let parsed: unknown;
          try {
            parsed = JSON.parse(value);
          } catch {
            return;
          }

          if (typeof parsed === 'object') {
            form.setFieldValue('params', parsed as Record<string, never>);
          }
        }}
        error={form.errors.params}
      />

      <Paper withBorder p="xs">
        <SamplesSection form={form} />
      </Paper>
      <Paper withBorder p="xs">
        <TemplatesSection form={form} />
      </Paper>
    </Stack>
  );
};
