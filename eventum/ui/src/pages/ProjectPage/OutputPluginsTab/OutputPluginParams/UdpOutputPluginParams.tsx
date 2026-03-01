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
  UdpOutputPluginConfig,
  UdpOutputPluginConfigSchema,
} from '@/api/routes/generator-configs/schemas/plugins/output/configs/udp';
import { LabelWithTooltip } from '@/components/ui/LabelWithTooltip';

interface UdpOutputPluginParamsProps {
  initialConfig: UdpOutputPluginConfig;
  onChange: (config: UdpOutputPluginConfig) => void;
}

export const UdpOutputPluginParams: FC<UdpOutputPluginParamsProps> = ({
  initialConfig,
  onChange,
}) => {
  const form = useForm<UdpOutputPluginConfig>({
    initialValues: initialConfig,
    validate: zod4Resolver(UdpOutputPluginConfigSchema),
    onValuesChange: onChange,
    validateInputOnChange: true,
  });

  return (
    <Stack gap="xs">
      <Group grow wrap="nowrap" align="start">
        <TextInput
          label={
            <LabelWithTooltip
              label="Host"
              tooltip="Hostname or IP address to send datagrams to"
            />
          }
          placeholder="hostname"
          required
          {...form.getInputProps('host')}
          value={form.values.host ?? ''}
          onChange={(value) =>
            form.setFieldValue(
              'host',
              value.currentTarget.value !== ''
                ? value.currentTarget.value
                : undefined!
            )
          }
        />

        <NumberInput
          label={
            <LabelWithTooltip
              label="Port"
              tooltip="UDP port number to send datagrams to"
            />
          }
          placeholder="port"
          required
          min={1}
          max={65_535}
          step={1}
          allowDecimal={false}
          {...form.getInputProps('port')}
          value={form.values.port ?? ''}
          onChange={(value) =>
            form.setFieldValue(
              'port',
              typeof value === 'number' ? value : undefined!
            )
          }
        />
      </Group>

      <Select
        label={
          <LabelWithTooltip
            label="Encoding"
            tooltip="Encoding used to encode events before sending. Default is UTF-8."
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
            tooltip="Separator appended after each event, default value is line separator defined by OS"
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
