import {
  ActionIcon,
  Group,
  Kbd,
  NumberInput,
  Paper,
  Select,
  Stack,
  Switch,
  Text,
  TextInput,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { zod4Resolver } from 'mantine-form-zod-resolver';
import { FC } from 'react';

import { ProjectFileSelect } from '../../components/ProjectFileSelect';
import { FormatterParams } from './components/FormatterParams';
import { ENCODINGS } from '@/api/routes/generator-configs/schemas/encodings';
import {
  TcpOutputPluginConfig,
  TcpOutputPluginConfigSchema,
} from '@/api/routes/generator-configs/schemas/plugins/output/configs/tcp';
import { LabelWithTooltip } from '@/components/ui/LabelWithTooltip';

interface TcpOutputPluginParamsProps {
  initialConfig: TcpOutputPluginConfig;
  onChange: (config: TcpOutputPluginConfig) => void;
}

export const TcpOutputPluginParams: FC<TcpOutputPluginParamsProps> = ({
  initialConfig,
  onChange,
}) => {
  const form = useForm<TcpOutputPluginConfig>({
    initialValues: initialConfig,
    validate: zod4Resolver(TcpOutputPluginConfigSchema),
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
              tooltip="Hostname or IP address to connect to"
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
              tooltip="TCP port number to connect to"
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

      <NumberInput
        label={
          <LabelWithTooltip
            label="Connect timeout"
            tooltip="Connection timeout in seconds, default value is 10"
          />
        }
        placeholder="seconds"
        suffix=" s."
        min={1}
        step={1}
        allowDecimal={false}
        {...form.getInputProps('connect_timeout')}
        value={form.getValues().connect_timeout ?? ''}
        onChange={(value) =>
          form.setFieldValue(
            'connect_timeout',
            typeof value === 'number' ? value : undefined
          )
        }
      />

      <Paper withBorder p="sm">
        <Stack gap="4px">
          <Text size="sm" fw="bold">
            SSL
          </Text>

          <Group>
            <Switch
              label={
                <LabelWithTooltip
                  label="Use SSL/TLS"
                  tooltip="Whether to use SSL/TLS for the connection"
                />
              }
              {...form.getInputProps('ssl', { type: 'checkbox' })}
              onChange={(event) => {
                const checked = event.currentTarget.checked;
                form.setFieldValue('ssl', checked);
                if (!checked) {
                  form.setFieldValue('verify', false);
                  form.setFieldValue('ca_cert', undefined);
                  form.setFieldValue('client_cert', undefined);
                  form.setFieldValue('client_cert_key', undefined);
                }
              }}
            />

            <Switch
              label={
                <LabelWithTooltip
                  label="Verify SSL"
                  tooltip="Whether to verify SSL certificate of the server when connecting to it"
                />
              }
              disabled={!form.getValues().ssl}
              {...form.getInputProps('verify', { type: 'checkbox' })}
            />
          </Group>

          <ProjectFileSelect
            label={
              <LabelWithTooltip
                label="CA certificate"
                tooltip="CA certificate for verification of server"
              />
            }
            placeholder=".crt .cer .pem"
            extensions={['.crt', '.cer', '.pem']}
            clearable
            searchable
            disabled={!form.getValues().ssl}
            {...form.getInputProps('ca_cert')}
            value={form.getValues().ca_cert ?? null}
            onChange={(value) =>
              form.setFieldValue('ca_cert', value ?? undefined)
            }
          />

          <Group grow align="start" wrap="nowrap">
            <ProjectFileSelect
              label={
                <LabelWithTooltip
                  label="Client certificate"
                  tooltip="Client certificate for client verification by server"
                />
              }
              placeholder=".crt .cer .pem"
              extensions={['.crt', '.cer', '.pem']}
              clearable
              searchable
              disabled={!form.getValues().ssl}
              {...form.getInputProps('client_cert')}
              value={form.getValues().client_cert ?? null}
              onChange={(value) =>
                form.setFieldValue('client_cert', value ?? undefined)
              }
            />
            <ProjectFileSelect
              label={
                <LabelWithTooltip
                  label="Client certificate key"
                  tooltip="Key for the client certificate"
                />
              }
              placeholder=".crt .cer .pem .key"
              extensions={['.crt', '.cer', '.pem', '.key']}
              clearable
              searchable
              disabled={!form.getValues().ssl}
              {...form.getInputProps('client_cert_key')}
              value={form.getValues().client_cert_key ?? null}
              onChange={(value) =>
                form.setFieldValue('client_cert_key', value ?? undefined)
              }
            />
          </Group>
        </Stack>
      </Paper>

      <Paper withBorder p="xs">
        <FormatterParams
          value={form.getValues().formatter}
          onChange={(values) => form.setFieldValue('formatter', values)}
        />
      </Paper>
    </Stack>
  );
};
