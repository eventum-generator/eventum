import {
  ActionIcon,
  Group,
  Kbd,
  NumberInput,
  Paper,
  SegmentedControl,
  Select,
  Stack,
  Text,
  TextInput,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { zod4Resolver } from 'mantine-form-zod-resolver';
import { FC } from 'react';

import { FormatterParams } from './components/FormatterParams';
import { ENCODINGS } from '@/api/routes/generator-configs/schemas/encodings';
import {
  StdoutOutputPluginConfig,
  StdoutOutputPluginConfigSchema,
} from '@/api/routes/generator-configs/schemas/plugins/output/configs/stdout';
import { LabelWithTooltip } from '@/components/ui/LabelWithTooltip';

interface StdoutOutputPluginParamsProps {
  initialConfig: StdoutOutputPluginConfig;
  onChange: (config: StdoutOutputPluginConfig) => void;
}

export const StdoutOutputPluginParams: FC<StdoutOutputPluginParamsProps> = ({
  initialConfig,
  onChange,
}) => {
  const form = useForm<StdoutOutputPluginConfig>({
    initialValues: initialConfig,
    validate: zod4Resolver(StdoutOutputPluginConfigSchema),
    onValuesChange: onChange,
    validateInputOnChange: true,
  });

  return (
    <Stack gap="xs">
      <Stack gap="4px">
        <Text size="sm">Stream</Text>
        <SegmentedControl
          data={['stdout', 'stderr']}
          {...form.getInputProps('stream')}
        />
      </Stack>

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
        onChange={(value) => form.setFieldValue('encoding', value ?? undefined)}
      />

      <TextInput
        label={
          <LabelWithTooltip
            label="Separator"
            tooltip="Events separator, default value is line separator defined by OS"
          />
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

      <Paper withBorder p="xs">
        <FormatterParams
          value={form.getValues().formatter}
          onChange={(values) => form.setFieldValue('formatter', values)}
        />
      </Paper>
    </Stack>
  );
};
