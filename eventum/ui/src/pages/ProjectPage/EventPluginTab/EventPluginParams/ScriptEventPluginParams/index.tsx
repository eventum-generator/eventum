import { Stack } from '@mantine/core';
import { useForm } from '@mantine/form';
import { zod4Resolver } from 'mantine-form-zod-resolver';
import { FC } from 'react';

import {
  ScriptEventPluginConfig,
  ScriptEventPluginConfigSchema,
} from '@/api/routes/generator-configs/schemas/plugins/event/configs/script';
import { LabelWithTooltip } from '@/components/ui/LabelWithTooltip';
import { ProjectFileSelect } from '@/pages/ProjectPage/components/ProjectFileSelect';

interface ScriptEventPluginParamsProps {
  initialConfig: ScriptEventPluginConfig;
  onChange: (config: ScriptEventPluginConfig) => void;
}

export const ScriptEventPluginParams: FC<ScriptEventPluginParamsProps> = ({
  initialConfig,
  onChange,
}) => {
  const form = useForm<ScriptEventPluginConfig>({
    initialValues: initialConfig,
    validate: zod4Resolver(ScriptEventPluginConfigSchema),
    onValuesChange: onChange,
    onSubmitPreventDefault: 'always',
    validateInputOnChange: true,
  });

  return (
    <Stack gap="xs">
      <ProjectFileSelect
        label={<LabelWithTooltip label="Path" tooltip="Path to script file" />}
        placeholder="path"
        clearable
        searchable
        extensions={['.py']}
        required
        {...form.getInputProps('path')}
        value={typeof form.values.path === 'string' ? form.values.path : null}
        onChange={(value) => {
          form.setFieldValue('path', value ?? undefined!);
        }}
      />
    </Stack>
  );
};
