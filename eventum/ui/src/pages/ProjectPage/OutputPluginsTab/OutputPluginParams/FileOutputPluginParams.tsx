import {
  ActionIcon,
  Group,
  Kbd,
  NumberInput,
  Paper,
  Select,
  Stack,
  TextInput,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { zod4Resolver } from 'mantine-form-zod-resolver';
import { FC } from 'react';

import { FormatterParams } from './components/FormatterParams';
import { ENCODINGS } from '@/api/routes/generator-configs/schemas/encodings';
import {
  FileOutputPluginConfig,
  FileOutputPluginConfigSchema,
  WRITE_MODES,
} from '@/api/routes/generator-configs/schemas/plugins/output/configs/file';
import { LabelWithTooltip } from '@/components/ui/LabelWithTooltip';

interface FileOutputPluginParamsProps {
  initialConfig: FileOutputPluginConfig;
  onChange: (config: FileOutputPluginConfig) => void;
}

export const FileOutputPluginParams: FC<FileOutputPluginParamsProps> = ({
  initialConfig,
  onChange,
}) => {
  const form = useForm<FileOutputPluginConfig>({
    initialValues: initialConfig,
    validate: zod4Resolver(FileOutputPluginConfigSchema),
    onValuesChange: onChange,
    validateInputOnChange: true,
  });

  return (
    <Stack gap="xs">
      <TextInput
        label={
          <LabelWithTooltip
            label="Path"
            tooltip="Path to the file for writing"
          />
        }
        required
        placeholder="file path"
        {...form.getInputProps('path')}
      />

      <Group grow wrap="nowrap" align="start">
        <NumberInput
          label={
            <LabelWithTooltip
              label="Flush interval"
              tooltip="Interval of events flushing, if value is set to 0 then flush is performed for every event, default value is 1"
            />
          }
          suffix=" s."
          min={0}
          step={0.1}
          {...form.getInputProps('flush_interval')}
          value={form.getValues().flush_interval ?? ''}
          onChange={(value) =>
            form.setFieldValue(
              'flush_interval',
              typeof value === 'number' ? value : undefined
            )
          }
        />
        <NumberInput
          label={
            <LabelWithTooltip
              label="Cleanup interval"
              tooltip="Interval of waiting new events before closing the file, file is reopened once new events are received, default value is 10"
            />
          }
          suffix=" s."
          min={1}
          step={0.1}
          {...form.getInputProps('cleanup_interval')}
          value={form.getValues().cleanup_interval ?? ''}
          onChange={(value) =>
            form.setFieldValue(
              'cleanup_interval',
              typeof value === 'number' ? value : undefined
            )
          }
        />
      </Group>

      <Group grow wrap="nowrap" align="start">
        <NumberInput
          label={
            <LabelWithTooltip
              label="File mode"
              tooltip="File access mode to use"
            />
          }
          min={0}
          max={7777}
          step={1}
          allowDecimal={false}
          {...form.getInputProps('file_mode')}
          value={form.getValues().file_mode ?? ''}
          onChange={(value) =>
            form.setFieldValue(
              'file_mode',
              typeof value === 'number' ? value : undefined
            )
          }
        />
        <Select
          label={
            <LabelWithTooltip
              label="Encoding"
              tooltip="Encoding of the file. Default is UTF-8."
            />
          }
          placeholder="encoding"
          data={ENCODINGS}
          clearable
          searchable
          {...form.getInputProps('encoding')}
          value={form.getValues().encoding ?? null}
          onChange={(value) =>
            form.setFieldValue('encoding', value ?? undefined)
          }
        />
      </Group>

      <Group grow wrap="nowrap" align="start">
        <TextInput
          label={
            <LabelWithTooltip label="Separator" tooltip="Events separator" />
          }
          rightSectionWidth="70px"
          rightSection={
            <Group wrap="nowrap" gap="2px">
              <ActionIcon
                variant="transparent"
                title="Set tabulation as delimiter"
                onClick={() => {
                  form.setFieldValue('separator', '\t');
                }}
              >
                <Kbd>\t</Kbd>
              </ActionIcon>
              <ActionIcon
                variant="transparent"
                title="Set LF as delimiter"
                onClick={() => {
                  form.setFieldValue('separator', '\n');
                }}
              >
                <Kbd>\n</Kbd>
              </ActionIcon>
            </Group>
          }
          {...form.getInputProps('separator')}
          onChange={(value) =>
            form.setFieldValue(
              'separator',
              value.currentTarget.value !== ''
                ? value.currentTarget.value
                : undefined
            )
          }
        />
        <Select
          label={
            <LabelWithTooltip
              label="Write mode"
              tooltip="Write behavior when the file already exists.
              In 'append' mode, new data is appended to the end of the file.
              In 'overwrite' mode, a new empty file is created on startup.
              Default value is 'append'."
            />
          }
          placeholder="mode"
          data={WRITE_MODES}
          clearable
          {...form.getInputProps('write_mode')}
          value={form.getValues().write_mode ?? null}
          onChange={(value) =>
            form.setFieldValue(
              'write_mode',
              (value ?? undefined) as (typeof WRITE_MODES)[number] | undefined
            )
          }
        />
      </Group>
      <Paper withBorder p="xs">
        <FormatterParams
          value={form.getValues().formatter}
          onChange={(values) => form.setFieldValue('formatter', values)}
        />
      </Paper>
    </Stack>
  );
};
