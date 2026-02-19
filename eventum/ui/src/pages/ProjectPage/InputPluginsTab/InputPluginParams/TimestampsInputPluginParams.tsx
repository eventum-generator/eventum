import { Box, Stack, Tabs, TagsInput, Textarea } from '@mantine/core';
import { useForm } from '@mantine/form';
import { zod4Resolver } from 'mantine-form-zod-resolver';
import { FC } from 'react';

import { ProjectFileSelect } from '../../components/ProjectFileSelect';
import {
  TimestampsInputPluginConfig,
  TimestampsInputPluginConfigSchema,
} from '@/api/routes/generator-configs/schemas/plugins/input/configs/timestamps';
import { LabelWithTooltip } from '@/components/ui/LabelWithTooltip';

interface TimestampsInputPluginParamsProps {
  initialConfig: TimestampsInputPluginConfig;
  onChange: (config: TimestampsInputPluginConfig) => void;
}

export const TimestampsInputPluginParams: FC<
  TimestampsInputPluginParamsProps
> = ({ initialConfig, onChange }) => {
  const form = useForm<TimestampsInputPluginConfig>({
    validate: zod4Resolver(TimestampsInputPluginConfigSchema),
    initialValues: initialConfig,
    onValuesChange: onChange,
    onSubmitPreventDefault: 'always',
    validateInputOnChange: true,
  });

  return (
    <Stack gap="xs">
      <Tabs defaultValue="inline">
        <Tabs.List>
          <Tabs.Tab value="inline">Inline</Tabs.Tab>
          <Tabs.Tab value="file">File</Tabs.Tab>
        </Tabs.List>

        <Box mt="xs">
          <Tabs.Panel value="inline">
            <Textarea
              label="Source"
              description="List of ISO8601 timestamps delimited by new line"
              placeholder="..."
              autosize
              minRows={3}
              required
              value={
                Array.isArray(form.values.source)
                  ? form.values.source.join('\n')
                  : ''
              }
              onChange={(event) => {
                form.setFieldValue(
                  'source',
                  event.currentTarget.value
                    ? event.currentTarget.value
                        .split('\n')
                        .map((item) => item.trim())
                    : []
                );
              }}
              error={form.errors.source}
            />
          </Tabs.Panel>
          <Tabs.Panel value="file">
            <ProjectFileSelect
              label={
                <LabelWithTooltip
                  label="Timestamps file"
                  tooltip="File with new line separated timestamps in ISO8601 format"
                />
              }
              placeholder=".csv .txt"
              extensions={['.csv', '.txt', 'timestamps']}
              clearable
              searchable
              required
              value={
                typeof form.values.source === 'string'
                  ? form.values.source
                  : null
              }
              onChange={(value) => {
                form.setFieldValue('source', value ?? undefined!);
              }}
              error={form.errors.source}
            />
          </Tabs.Panel>
        </Box>
      </Tabs>
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
