import {
  ActionIcon,
  Anchor,
  Center,
  Group,
  Kbd,
  NumberInput,
  Paper,
  PasswordInput,
  SegmentedControl,
  Select,
  Stack,
  Switch,
  Text,
  TextInput,
  Textarea,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { IconLock, IconLockOff } from '@tabler/icons-react';
import { zod4Resolver } from 'mantine-form-zod-resolver';
import { FC, ReactNode } from 'react';

import { ProjectFileSelect } from '../../components/ProjectFileSelect';
import { FormatterParams } from './components/FormatterParams';
import {
  ClickhouseOutputPluginConfig,
  ClickhouseOutputPluginConfigSchema,
  PROTOCOLS,
  TLS_MODES,
} from '@/api/routes/generator-configs/schemas/plugins/output/configs/clickhouse';
import { CLICKHOUSE_INPUT_FORMAT } from '@/api/routes/generator-configs/schemas/plugins/output/configs/clickhouse/clickhouse-input-formats';
import { LabelWithTooltip } from '@/components/ui/LabelWithTooltip';

interface ClickhouseOutputPluginParamsProps {
  initialConfig: ClickhouseOutputPluginConfig;
  onChange: (config: ClickhouseOutputPluginConfig) => void;
}

export const ClickhouseOutputPluginParams: FC<
  ClickhouseOutputPluginParamsProps
> = ({ initialConfig, onChange }) => {
  const form = useForm<ClickhouseOutputPluginConfig>({
    initialValues: initialConfig,
    validate: zod4Resolver(ClickhouseOutputPluginConfigSchema),
    onValuesChange: onChange,
    validateInputOnChange: true,
  });

  return (
    <Stack gap="xs">
      <Group grow align="start">
        <TextInput
          label={
            <LabelWithTooltip
              label="Host"
              tooltip="The hostname or IP address of the ClickHouse server"
            />
          }
          required
          placeholder="ip or hostname"
          {...form.getInputProps('host')}
        />
        <NumberInput
          label={
            <LabelWithTooltip
              label="Port"
              tooltip="The ClickHouse HTTP or HTTPS port, default value is 8123"
            />
          }
          min={1}
          max={65_535}
          step={1}
          allowDecimal={false}
          {...form.getInputProps('port')}
          value={form.getValues().port ?? ''}
          onChange={(value) =>
            form.setFieldValue(
              'port',
              typeof value === 'number' ? value : undefined
            )
          }
        />
      </Group>

      <Stack gap="4px">
        <Text size="sm">Protocol</Text>
        <SegmentedControl
          data={
            [
              {
                label: (
                  <Center>
                    <Group gap="4px">
                      <IconLockOff size={14} />
                      <span>HTTP</span>
                    </Group>
                  </Center>
                ),
                value: 'http',
              },
              {
                label: (
                  <Center>
                    <Group gap="4px">
                      <IconLock size={14} />
                      <span>HTTPS</span>
                    </Group>
                  </Center>
                ),
                value: 'https',
              },
            ] as const satisfies {
              label: ReactNode;
              value: (typeof PROTOCOLS)[number];
            }[]
          }
          {...form.getInputProps('protocol')}
        />
      </Stack>

      <Group grow align="start" wrap="nowrap">
        <TextInput
          label={
            <LabelWithTooltip
              label="Database"
              tooltip="Database name, default value is 'default'"
            />
          }
          placeholder="name"
          {...form.getInputProps('database')}
          onChange={(value) =>
            form.setFieldValue(
              'database',
              value.currentTarget.value !== ''
                ? value.currentTarget.value
                : undefined
            )
          }
        />
        <TextInput
          label={<LabelWithTooltip label="Table" tooltip="Table name" />}
          required
          placeholder="name"
          {...form.getInputProps('table')}
        />
      </Group>

      <Group align="start" wrap="nowrap" grow>
        <TextInput
          label={
            <LabelWithTooltip
              label="Username"
              tooltip="Username that is used to authenticate to ClickHouse, default value is 'default'"
            />
          }
          {...form.getInputProps('username')}
          onChange={(value) =>
            form.setFieldValue(
              'username',
              value.currentTarget.value !== ''
                ? value.currentTarget.value
                : undefined
            )
          }
        />
        <PasswordInput
          label={
            <LabelWithTooltip
              label="Password"
              tooltip="Password for user to authenticate, default is ''"
            />
          }
          {...form.getInputProps('password')}
          onChange={(value) =>
            form.setFieldValue(
              'password',
              value.currentTarget.value !== ''
                ? value.currentTarget.value
                : undefined
            )
          }
        />
      </Group>

      <Textarea
        label="DSN"
        description="A string in standard DSN (Data Source Name) format, other
              connection values (such as host or username) will be extracted
              from this string if not set otherwise."
        placeholder="clickhouse://..."
        autosize
        minRows={2}
        {...form.getInputProps('dsn')}
        onChange={(value) =>
          form.setFieldValue(
            'dsn',
            value.currentTarget.value !== ''
              ? value.currentTarget.value
              : undefined
          )
        }
      />

      <Group grow wrap="nowrap" align="start">
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
        <NumberInput
          label={
            <LabelWithTooltip
              label="Request timeout"
              tooltip="Request timeout in seconds, default value is 300"
            />
          }
          placeholder="seconds"
          suffix=" s."
          min={1}
          step={1}
          allowDecimal={false}
          {...form.getInputProps('request_timeout')}
          value={form.getValues().request_timeout ?? ''}
          onChange={(value) =>
            form.setFieldValue(
              'request_timeout',
              typeof value === 'number' ? value : undefined
            )
          }
        />
      </Group>

      <TextInput
        label={
          <LabelWithTooltip
            label="Client name"
            tooltip="Client name that is prepended to the HTTP User Agent header,
              set this to track client queries in the ClickHouse query log"
          />
        }
        placeholder="name"
        {...form.getInputProps('client_name')}
        onChange={(value) =>
          form.setFieldValue(
            'client_name',
            value.currentTarget.value !== ''
              ? value.currentTarget.value
              : undefined
          )
        }
      />

      <Paper withBorder p="xs">
        <Stack gap="xs">
          <Text size="sm" fw="bold">
            SSL
          </Text>

          <Switch
            label={
              <LabelWithTooltip
                label="Verify SSL"
                tooltip="Whether to verify SSL certificate of ClickHouse server"
              />
            }
            {...form.getInputProps('verify', { type: 'checkbox' })}
          />

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
              {...form.getInputProps('client_cert_key')}
              value={form.getValues().client_cert_key ?? null}
              onChange={(value) =>
                form.setFieldValue('client_cert_key', value ?? undefined)
              }
            />
          </Group>

          <Select
            label={
              <LabelWithTooltip
                label="TLS mode"
                tooltip="Mode of TLS behavior, `proxy` and `strict` do not invoke
                  ClickHouse mutual TLS connection, but do send client cert and
                  key, `mutual` assumes ClickHouse mutual TLS auth with a client
                  certificate, default behavior is `mutual`."
              />
            }
            placeholder="mode"
            data={TLS_MODES}
            clearable
            searchable
            {...form.getInputProps('tls_mode')}
            value={form.getValues().tls_mode ?? null}
            onChange={(value) =>
              form.setFieldValue(
                'tls_mode',
                (value ?? undefined) as (typeof TLS_MODES)[number] | undefined
              )
            }
          />
        </Stack>
      </Paper>

      <Paper withBorder p="xs">
        <Stack gap="xs">
          <Text size="sm" fw="bold">
            Proxy
          </Text>

          <TextInput
            label={
              <LabelWithTooltip
                label="Server host name"
                tooltip="The ClickHouse server hostname as identified by the CN or SNI
            of its TLS certificate, set this to avoid SSL errors when
            connecting through a proxy or tunnel with a different hostname."
              />
            }
            placeholder="ip or hostname"
            {...form.getInputProps('server_host_name')}
            onChange={(value) =>
              form.setFieldValue(
                'server_host_name',
                value.currentTarget.value !== ''
                  ? value.currentTarget.value
                  : undefined
              )
            }
          />
          <TextInput
            label={
              <LabelWithTooltip
                label="Proxy URL"
                tooltip="HTTP(S) proxy address"
              />
            }
            placeholder="URL"
            {...form.getInputProps('proxy_url')}
            onChange={(value) =>
              form.setFieldValue(
                'proxy_url',
                value.currentTarget.value !== ''
                  ? value.currentTarget.value
                  : undefined
              )
            }
          />
        </Stack>
      </Paper>

      <Paper withBorder p="xs">
        <Stack gap="xs">
          <Text size="sm" fw="bold">
            Format
          </Text>

          <Select
            label={
              <Group>
                <LabelWithTooltip
                  label="Input format"
                  tooltip="ClickHouse input format for inserting, default values is 'JSONEachRow'"
                />

                <Anchor
                  size="sm"
                  target="_blank"
                  href="https://clickhouse.com/docs/en/interfaces/formats"
                >
                  ClickHouse formats
                </Anchor>
              </Group>
            }
            placeholder="format"
            data={CLICKHOUSE_INPUT_FORMAT}
            clearable
            searchable
            {...form.getInputProps('input_format')}
            value={form.getValues().input_format ?? null}
            onChange={(value) => {
              form.setFieldValue('input_format', value ?? undefined);
            }}
          />

          <Textarea
            label="Header"
            description="Header that inserted before all events"
            autosize
            minRows={1}
            {...form.getInputProps('header')}
            onChange={(value) =>
              form.setFieldValue(
                'header',
                value.currentTarget.value !== ''
                  ? value.currentTarget.value
                  : undefined
              )
            }
          />
          <TextInput
            label={
              <LabelWithTooltip
                label="Separator"
                tooltip="Separator between events, default value is new line"
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
          <Textarea
            label="Footer"
            description="Footer that inserted after all events"
            autosize
            minRows={1}
            {...form.getInputProps('footer')}
            onChange={(value) =>
              form.setFieldValue(
                'footer',
                value.currentTarget.value !== ''
                  ? value.currentTarget.value
                  : undefined
              )
            }
          />

          <FormatterParams
            value={form.getValues().formatter}
            onChange={(values) => form.setFieldValue('formatter', values)}
          />
        </Stack>
      </Paper>
    </Stack>
  );
};
