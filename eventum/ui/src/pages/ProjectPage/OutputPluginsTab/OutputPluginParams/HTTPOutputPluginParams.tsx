import {
  Group,
  JsonInput,
  NumberInput,
  Paper,
  PasswordInput,
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
import { FileOutputPluginConfigSchema } from '@/api/routes/generator-configs/schemas/plugins/output/configs/file';
import {
  HTTPOutputPluginConfig,
  HTTP_METHODS,
} from '@/api/routes/generator-configs/schemas/plugins/output/configs/http';
import { LabelWithTooltip } from '@/components/ui/LabelWithTooltip';

interface HTTPOutputPluginParamsProps {
  initialConfig: HTTPOutputPluginConfig;
  onChange: (config: HTTPOutputPluginConfig) => void;
}

export const HTTPOutputPluginParams: FC<HTTPOutputPluginParamsProps> = ({
  initialConfig,
  onChange,
}) => {
  const form = useForm<HTTPOutputPluginConfig>({
    initialValues: initialConfig,
    validate: zod4Resolver(FileOutputPluginConfigSchema),
    onValuesChange: onChange,
    validateInputOnChange: true,
  });

  return (
    <Stack gap="xs">
      <TextInput
        label={
          <LabelWithTooltip label="URL" tooltip="URL address of resource" />
        }
        placeholder="url address"
        required
        {...form.getInputProps('url')}
        value={form.values.url ?? ''}
        onChange={(value) =>
          form.setFieldValue(
            'url',
            value.currentTarget.value !== ''
              ? value.currentTarget.value
              : undefined!
          )
        }
      />

      <Group grow wrap="nowrap" align="start">
        <Select
          label={
            <LabelWithTooltip label="Method" tooltip="HTTP method to use" />
          }
          placeholder="mode"
          data={HTTP_METHODS}
          clearable
          {...form.getInputProps('method')}
          value={form.values.method ?? null}
          onChange={(value) => form.setFieldValue('method', value ?? undefined)}
        />

        <NumberInput
          label={
            <LabelWithTooltip
              label="Success code"
              tooltip="Expected HTTP response code, if server returns other code, then
              it is considered as an error. Default value is 201."
            />
          }
          min={100}
          step={1}
          allowDecimal={false}
          {...form.getInputProps('success_code')}
          value={form.values.success_code ?? ''}
          onChange={(value) =>
            form.setFieldValue(
              'success_code',
              typeof value === 'number' ? value : undefined
            )
          }
        />
      </Group>

      <JsonInput
        label="Headers"
        description="Request headers"
        placeholder="{ ... }"
        validationError="Invalid JSON"
        minRows={2}
        autosize
        defaultValue={JSON.stringify(form.values.headers, undefined, 2)}
        onChange={(value) => {
          if (!value) {
            form.setFieldValue('headers', undefined);
            return;
          }

          let parsed: unknown;
          try {
            parsed = JSON.parse(value);
          } catch {
            return;
          }

          if (typeof parsed === 'object') {
            form.setFieldValue('headers', parsed as Record<string, unknown>);
          }
        }}
        error={form.errors.headers}
      />

      <Group align="start" wrap="nowrap" grow>
        <TextInput
          label={
            <LabelWithTooltip
              label="Username"
              tooltip="Username that is used to authenticate to ClickHouse"
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
              tooltip="Password for user to authenticate"
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

      <Paper withBorder p="sm">
        <Stack gap="4px">
          <Text size="sm" fw="bold">
            SSL
          </Text>

          <Switch
            label={
              <LabelWithTooltip
                label="Verify SSL"
                tooltip="Whether to verify SSL certificate of the server when
            connecting to it"
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
        </Stack>
      </Paper>

      <TextInput
        label={
          <LabelWithTooltip label="Proxy URL" tooltip="HTTP(S) proxy address" />
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

      <Paper withBorder p="xs">
        <FormatterParams
          value={form.getValues().formatter}
          onChange={(values) => form.setFieldValue('formatter', values)}
        />
      </Paper>
    </Stack>
  );
};
