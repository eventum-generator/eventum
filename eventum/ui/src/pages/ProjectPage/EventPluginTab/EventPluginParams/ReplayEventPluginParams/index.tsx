import {
  Anchor,
  Group,
  NumberInput,
  Select,
  Stack,
  Switch,
  TextInput,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { zod4Resolver } from 'mantine-form-zod-resolver';
import { FC } from 'react';

import { ENCODINGS } from '@/api/routes/generator-configs/schemas/encodings';
import {
  ReplayEventPluginConfig,
  ReplayEventPluginConfigSchema,
} from '@/api/routes/generator-configs/schemas/plugins/event/configs/replay';
import { LabelWithTooltip } from '@/components/ui/LabelWithTooltip';
import { ProjectFileSelect } from '@/pages/ProjectPage/components/ProjectFileSelect';

interface ReplayEventPluginParamsProps {
  initialConfig: ReplayEventPluginConfig;
  onChange: (config: ReplayEventPluginConfig) => void;
}

export const ReplayEventPluginParams: FC<ReplayEventPluginParamsProps> = ({
  initialConfig,
  onChange,
}) => {
  const form = useForm<ReplayEventPluginConfig>({
    initialValues: initialConfig,
    validate: zod4Resolver(ReplayEventPluginConfigSchema),
    onValuesChange: onChange,
    onSubmitPreventDefault: 'always',
    validateInputOnChange: true,
  });

  return (
    <Stack gap="xs">
      <ProjectFileSelect
        label={
          <LabelWithTooltip label="Path" tooltip="Path to log file to replay" />
        }
        placeholder="path"
        clearable
        searchable
        required
        {...form.getInputProps('path')}
        value={form.getValues().path ?? null}
        onChange={(value) => form.setFieldValue('path', value ?? undefined!)}
      />
      <TextInput
        label={
          <Group gap="xs">
            <LabelWithTooltip
              label="Timestamp pattern"
              tooltip="Regular expression pattern to identify the timestamp
                  substitution position within the original message. The
                  substitution is performed over the named group `timestamp`.
                  If value is not set or pattern does not match, then substitution
                  is not performed. Regular expression must be specified in Python regex dialect."
            />
            <Anchor
              size="sm"
              target="_blank"
              href="https://docs.python.org/3/library/re.html#regular-expression-syntax"
            >
              Regex syntax
            </Anchor>
          </Group>
        }
        placeholder="regular expression"
        {...form.getInputProps('timestamp_pattern')}
        onChange={(value) =>
          form.setFieldValue(
            'timestamp_pattern',
            value.currentTarget.value !== ''
              ? value.currentTarget.value
              : undefined
          )
        }
      />
      <TextInput
        label={
          <Group>
            <LabelWithTooltip
              label="Timestamp format"
              tooltip="Format string that defines how the actual timestamp should be substituted
                  in the log message. The format follows C89 standard. If value is not set, then
                  default (ISO 8601) format is used."
            />
            <Anchor
              size="sm"
              target="_blank"
              href="https://docs.python.org/3/library/datetime.html#strftime-and-strptime-format-codes"
            >
              C89 format
            </Anchor>
          </Group>
        }
        placeholder="format string"
        {...form.getInputProps('timestamp_format')}
        onChange={(value) =>
          form.setFieldValue(
            'timestamp_format',
            value.currentTarget.value !== ''
              ? value.currentTarget.value
              : undefined
          )
        }
      />
      <Switch
        label={
          <LabelWithTooltip
            label="Repeat"
            tooltip="Whether to repeat replaying after the end of file is reached."
          />
        }
        {...form.getInputProps('repeat', { type: 'checkbox' })}
      />
      <NumberInput
        label={
          <LabelWithTooltip
            label="Chunk size"
            tooltip="Number of bytes to read from the file at a time. This parameter
                controls how often to access file and how many data will be
                stored in in memory. If 0 is provided then the entire file is
                read at once. Default is 1 MiB."
          />
        }
        min={0}
        allowDecimal={false}
        placeholder="bytes"
        {...form.getInputProps('chunk_size')}
        value={form.getValues().chunk_size ?? ''}
        onChange={(value) =>
          form.setFieldValue(
            'chunk_size',
            typeof value === 'number' ? value : undefined
          )
        }
      />
      <Select
        label={
          <LabelWithTooltip
            label="Encoding"
            tooltip="Encoding of the log file. Default is UTF-8."
          />
        }
        placeholder="encoding"
        data={ENCODINGS}
        clearable
        searchable
        {...form.getInputProps('encoding')}
        value={form.getValues().encoding ?? null}
        onChange={(value) => form.setFieldValue('encoding', value ?? undefined)}
      />
    </Stack>
  );
};
