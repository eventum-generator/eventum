import {
  Group,
  JsonInput,
  NumberInput,
  Paper,
  PasswordInput,
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
import {
  OpensearchOutputPluginConfig,
  OpensearchOutputPluginConfigSchema,
} from '@/api/routes/generator-configs/schemas/plugins/output/configs/opensearch';
import { LabelWithTooltip } from '@/components/ui/LabelWithTooltip';

interface OpensearchOutputPluginParamsProps {
  initialConfig: OpensearchOutputPluginConfig;
  onChange: (config: OpensearchOutputPluginConfig) => void;
}

export const OpensearchOutputPluginParams: FC<
  OpensearchOutputPluginParamsProps
> = ({ initialConfig, onChange }) => {
  const form = useForm<OpensearchOutputPluginConfig>({
    initialValues: initialConfig,
    validate: zod4Resolver(OpensearchOutputPluginConfigSchema),
    onValuesChange: onChange,
    validateInputOnChange: true,
  });

  return (
    <Stack gap="xs">
      <JsonInput
        label="Hosts"
        description={
          <LabelWithTooltip
            label="OpenSearch cluster nodes that will be used for indexing events"
            tooltip='Specifying more than one nodes allows for load balancing,
            nodes must be specified as list of elements in format "https://<host>:<port>"'
          />
        }
        placeholder="[ ... ]"
        validationError="Invalid JSON"
        minRows={2}
        autosize
        required
        defaultValue={JSON.stringify(form.values.hosts)}
        onChange={(value) => {
          if (!value) {
            form.setFieldValue('hosts', undefined!);
            return;
          }

          let parsed: unknown;
          try {
            parsed = JSON.parse(value);
          } catch {
            return;
          }

          if (Array.isArray(parsed)) {
            form.setFieldValue('hosts', parsed);
          }
        }}
        error={form.errors.hosts}
      />

      <TextInput
        label={
          <LabelWithTooltip label="Index" tooltip="Index for writing events" />
        }
        required
        {...form.getInputProps('index')}
        onChange={(value) =>
          form.setFieldValue(
            'index',
            value.currentTarget.value !== ''
              ? value.currentTarget.value
              : undefined!
          )
        }
      />

      <Group align="start" wrap="nowrap" grow>
        <TextInput
          label={
            <LabelWithTooltip
              label="Username"
              tooltip="Username that is used to authenticate to OpenSearch"
            />
          }
          required
          {...form.getInputProps('username')}
          onChange={(value) =>
            form.setFieldValue(
              'username',
              value.currentTarget.value !== ''
                ? value.currentTarget.value
                : undefined!
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
          required
          {...form.getInputProps('password')}
          onChange={(value) =>
            form.setFieldValue(
              'password',
              value.currentTarget.value !== ''
                ? value.currentTarget.value
                : undefined!
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

      <Paper withBorder p="xs">
        <Stack gap="xs">
          <Text size="sm" fw="bold">
            SSL
          </Text>
          <Switch
            label={
              <LabelWithTooltip
                label="Verify SSL"
                tooltip="Whether to verify SSL certificate of the cluster nodes when
            connecting to them"
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

      <Paper withBorder p="xs">
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
