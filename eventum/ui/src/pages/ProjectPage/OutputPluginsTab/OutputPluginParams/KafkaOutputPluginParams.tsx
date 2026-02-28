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
import { ENCODINGS } from '@/api/routes/generator-configs/schemas/encodings';
import {
  COMPRESSION_TYPES,
  KafkaOutputPluginConfig,
  KafkaOutputPluginConfigSchema,
  SASL_MECHANISMS,
  SECURITY_PROTOCOLS,
} from '@/api/routes/generator-configs/schemas/plugins/output/configs/kafka';
import { LabelWithTooltip } from '@/components/ui/LabelWithTooltip';

interface KafkaOutputPluginParamsProps {
  initialConfig: KafkaOutputPluginConfig;
  onChange: (config: KafkaOutputPluginConfig) => void;
}

export const KafkaOutputPluginParams: FC<KafkaOutputPluginParamsProps> = ({
  initialConfig,
  onChange,
}) => {
  const form = useForm<KafkaOutputPluginConfig>({
    initialValues: initialConfig,
    validate: zod4Resolver(KafkaOutputPluginConfigSchema),
    onValuesChange: onChange,
    validateInputOnChange: true,
  });

  return (
    <Stack gap="xs">
      <JsonInput
        label={
          <LabelWithTooltip
            label="Bootstrap servers"
            tooltip='Kafka broker addresses in host:port format, e.g. ["broker1:9092", "broker2:9092"]'
          />
        }
        placeholder="[ ... ]"
        validationError="Invalid JSON"
        minRows={2}
        autosize
        required
        defaultValue={JSON.stringify(form.values.bootstrap_servers, undefined, 2)}
        onChange={(value) => {
          if (!value) {
            form.setFieldValue('bootstrap_servers', undefined!);
            return;
          }

          let parsed: unknown;
          try {
            parsed = JSON.parse(value);
          } catch {
            return;
          }

          if (Array.isArray(parsed)) {
            form.setFieldValue('bootstrap_servers', parsed);
          }
        }}
        error={form.errors.bootstrap_servers}
      />

      <Group grow wrap="nowrap" align="start">
        <TextInput
          label={
            <LabelWithTooltip
              label="Topic"
              tooltip="Target Kafka topic to produce messages to"
            />
          }
          placeholder="topic name"
          required
          {...form.getInputProps('topic')}
        />
        <TextInput
          label={
            <LabelWithTooltip
              label="Key"
              tooltip="Message key applied to all produced messages"
            />
          }
          placeholder="message key"
          {...form.getInputProps('key')}
          onChange={(value) =>
            form.setFieldValue(
              'key',
              value.currentTarget.value !== ''
                ? value.currentTarget.value
                : undefined,
            )
          }
        />
      </Group>

      <Select
        label={
          <LabelWithTooltip
            label="Encoding"
            tooltip="Encoding for converting event strings and keys to bytes, default is utf-8"
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

      <TextInput
        label={
          <LabelWithTooltip
            label="Client ID"
            tooltip="Client name passed in each request to brokers"
          />
        }
        placeholder="client name"
        {...form.getInputProps('client_id')}
        onChange={(value) =>
          form.setFieldValue(
            'client_id',
            value.currentTarget.value !== ''
              ? value.currentTarget.value
              : undefined,
          )
        }
      />

      <Paper withBorder p="xs">
        <Stack gap="xs">
          <Text size="sm" fw="bold">
            Performance
          </Text>

          <Group grow wrap="nowrap" align="start">
            <Select
              label={
                <LabelWithTooltip
                  label="Acks"
                  tooltip="Acknowledgments: 0 = fire-and-forget, 1 = leader only, -1 = all replicas"
                />
              }
              placeholder="acks"
              data={[
                { value: '0', label: '0 (none)' },
                { value: '1', label: '1 (leader)' },
                { value: '-1', label: '-1 (all)' },
              ]}
              clearable
              value={
                form.getValues().acks !== undefined
                  ? String(form.getValues().acks)
                  : null
              }
              onChange={(value) =>
                form.setFieldValue(
                  'acks',
                  value !== null ? Number(value) : undefined,
                )
              }
            />
            <Select
              label={
                <LabelWithTooltip
                  label="Compression"
                  tooltip="Compression codec for all produced data"
                />
              }
              placeholder="type"
              data={[...COMPRESSION_TYPES]}
              clearable
              {...form.getInputProps('compression_type')}
              value={form.getValues().compression_type ?? null}
              onChange={(value) =>
                form.setFieldValue('compression_type', value ?? undefined)
              }
            />
          </Group>

          <Group grow wrap="nowrap" align="start">
            <NumberInput
              label={
                <LabelWithTooltip
                  label="Max batch size"
                  tooltip="Maximum size of buffered data per partition in bytes, default is 16384"
                />
              }
              placeholder="bytes"
              suffix=" B"
              min={1}
              step={1024}
              allowDecimal={false}
              {...form.getInputProps('max_batch_size')}
              value={form.getValues().max_batch_size ?? ''}
              onChange={(value) =>
                form.setFieldValue(
                  'max_batch_size',
                  typeof value === 'number' ? value : undefined,
                )
              }
            />
            <NumberInput
              label={
                <LabelWithTooltip
                  label="Max request size"
                  tooltip="Maximum size of a produce request in bytes, default is 1048576"
                />
              }
              placeholder="bytes"
              suffix=" B"
              min={1}
              step={1024}
              allowDecimal={false}
              {...form.getInputProps('max_request_size')}
              value={form.getValues().max_request_size ?? ''}
              onChange={(value) =>
                form.setFieldValue(
                  'max_request_size',
                  typeof value === 'number' ? value : undefined,
                )
              }
            />
          </Group>

          <Group grow wrap="nowrap" align="start">
            <NumberInput
              label={
                <LabelWithTooltip
                  label="Linger"
                  tooltip="Artificial delay to allow batching in milliseconds, default is 0"
                />
              }
              placeholder="ms"
              suffix=" ms"
              min={0}
              step={10}
              allowDecimal={false}
              {...form.getInputProps('linger_ms')}
              value={form.getValues().linger_ms ?? ''}
              onChange={(value) =>
                form.setFieldValue(
                  'linger_ms',
                  typeof value === 'number' ? value : undefined,
                )
              }
            />
            <NumberInput
              label={
                <LabelWithTooltip
                  label="Retry backoff"
                  tooltip="Backoff between retries on errors in milliseconds, default is 100"
                />
              }
              placeholder="ms"
              suffix=" ms"
              min={0}
              step={50}
              allowDecimal={false}
              {...form.getInputProps('retry_backoff_ms')}
              value={form.getValues().retry_backoff_ms ?? ''}
              onChange={(value) =>
                form.setFieldValue(
                  'retry_backoff_ms',
                  typeof value === 'number' ? value : undefined,
                )
              }
            />
          </Group>

          <Group grow wrap="nowrap" align="start">
            <NumberInput
              label={
                <LabelWithTooltip
                  label="Request timeout"
                  tooltip="Produce request timeout in milliseconds, default is 40000"
                />
              }
              placeholder="ms"
              suffix=" ms"
              min={1}
              step={1000}
              allowDecimal={false}
              {...form.getInputProps('request_timeout_ms')}
              value={form.getValues().request_timeout_ms ?? ''}
              onChange={(value) =>
                form.setFieldValue(
                  'request_timeout_ms',
                  typeof value === 'number' ? value : undefined,
                )
              }
            />
            <NumberInput
              label={
                <LabelWithTooltip
                  label="Metadata max age"
                  tooltip="Period after which metadata is force-refreshed in milliseconds, default is 300000"
                />
              }
              placeholder="ms"
              suffix=" ms"
              min={0}
              step={10000}
              allowDecimal={false}
              {...form.getInputProps('metadata_max_age_ms')}
              value={form.getValues().metadata_max_age_ms ?? ''}
              onChange={(value) =>
                form.setFieldValue(
                  'metadata_max_age_ms',
                  typeof value === 'number' ? value : undefined,
                )
              }
            />
          </Group>

          <NumberInput
            label={
              <LabelWithTooltip
                label="Connections max idle"
                tooltip="Close idle connections after this time in milliseconds, default is 540000"
              />
            }
            placeholder="ms"
            suffix=" ms"
            min={0}
            step={10000}
            allowDecimal={false}
            {...form.getInputProps('connections_max_idle_ms')}
            value={form.getValues().connections_max_idle_ms ?? ''}
            onChange={(value) =>
              form.setFieldValue(
                'connections_max_idle_ms',
                typeof value === 'number' ? value : undefined,
              )
            }
          />

          <Switch
            label={
              <LabelWithTooltip
                label="Enable idempotence"
                tooltip="Ensure exactly one copy of each message is written"
              />
            }
            {...form.getInputProps('enable_idempotence', { type: 'checkbox' })}
          />

          <Group grow wrap="nowrap" align="start">
            <TextInput
              label={
                <LabelWithTooltip
                  label="Transactional ID"
                  tooltip="Transactional producer identifier"
                />
              }
              placeholder="txn id"
              {...form.getInputProps('transactional_id')}
              onChange={(value) =>
                form.setFieldValue(
                  'transactional_id',
                  value.currentTarget.value !== ''
                    ? value.currentTarget.value
                    : undefined,
                )
              }
            />
            <NumberInput
              label={
                <LabelWithTooltip
                  label="Transaction timeout"
                  tooltip="Transaction timeout in milliseconds, default is 60000"
                />
              }
              placeholder="ms"
              suffix=" ms"
              min={1}
              step={1000}
              allowDecimal={false}
              {...form.getInputProps('transaction_timeout_ms')}
              value={form.getValues().transaction_timeout_ms ?? ''}
              onChange={(value) =>
                form.setFieldValue(
                  'transaction_timeout_ms',
                  typeof value === 'number' ? value : undefined,
                )
              }
            />
          </Group>
        </Stack>
      </Paper>

      <Paper withBorder p="xs">
        <Stack gap="xs">
          <Text size="sm" fw="bold">
            Security
          </Text>

          <Select
            label={
              <LabelWithTooltip
                label="Security protocol"
                tooltip="Protocol used to communicate with brokers"
              />
            }
            placeholder="protocol"
            data={[...SECURITY_PROTOCOLS]}
            clearable
            {...form.getInputProps('security_protocol')}
            value={form.getValues().security_protocol ?? null}
            onChange={(value) =>
              form.setFieldValue('security_protocol', value ?? undefined)
            }
          />

          <Group grow wrap="nowrap" align="start">
            <Select
              label={
                <LabelWithTooltip
                  label="SASL mechanism"
                  tooltip="SASL authentication mechanism"
                />
              }
              placeholder="mechanism"
              data={[...SASL_MECHANISMS]}
              clearable
              {...form.getInputProps('sasl_mechanism')}
              value={form.getValues().sasl_mechanism ?? null}
              onChange={(value) =>
                form.setFieldValue('sasl_mechanism', value ?? undefined)
              }
            />
            <TextInput
              label={
                <LabelWithTooltip
                  label="Kerberos service name"
                  tooltip="Kerberos service name, default is 'kafka'"
                />
              }
              placeholder="service"
              {...form.getInputProps('sasl_kerberos_service_name')}
              onChange={(value) =>
                form.setFieldValue(
                  'sasl_kerberos_service_name',
                  value.currentTarget.value !== ''
                    ? value.currentTarget.value
                    : undefined,
                )
              }
            />
          </Group>

          <Group grow wrap="nowrap" align="start">
            <TextInput
              label={
                <LabelWithTooltip
                  label="SASL username"
                  tooltip="Username for SASL PLAIN authentication"
                />
              }
              placeholder="username"
              {...form.getInputProps('sasl_plain_username')}
              onChange={(value) =>
                form.setFieldValue(
                  'sasl_plain_username',
                  value.currentTarget.value !== ''
                    ? value.currentTarget.value
                    : undefined,
                )
              }
            />
            <PasswordInput
              label={
                <LabelWithTooltip
                  label="SASL password"
                  tooltip="Password for SASL PLAIN authentication"
                />
              }
              {...form.getInputProps('sasl_plain_password')}
              onChange={(value) =>
                form.setFieldValue(
                  'sasl_plain_password',
                  value.currentTarget.value !== ''
                    ? value.currentTarget.value
                    : undefined,
                )
              }
            />
          </Group>

          <TextInput
            label={
              <LabelWithTooltip
                label="Kerberos domain name"
                tooltip="Kerberos domain name"
              />
            }
            placeholder="domain"
            {...form.getInputProps('sasl_kerberos_domain_name')}
            onChange={(value) =>
              form.setFieldValue(
                'sasl_kerberos_domain_name',
                value.currentTarget.value !== ''
                  ? value.currentTarget.value
                  : undefined,
              )
            }
          />
        </Stack>
      </Paper>

      <Paper withBorder p="xs">
        <Stack gap="xs">
          <Text size="sm" fw="bold">
            SSL
          </Text>

          <ProjectFileSelect
            label={
              <LabelWithTooltip
                label="CA certificate"
                tooltip="Path to CA certificate file"
              />
            }
            placeholder=".crt .cer .pem"
            extensions={['.crt', '.cer', '.pem']}
            clearable
            searchable
            {...form.getInputProps('ssl_cafile')}
            value={form.getValues().ssl_cafile ?? null}
            onChange={(value) =>
              form.setFieldValue('ssl_cafile', value ?? undefined)
            }
          />

          <Group grow align="start" wrap="nowrap">
            <ProjectFileSelect
              label={
                <LabelWithTooltip
                  label="Client certificate"
                  tooltip="Path to client certificate file"
                />
              }
              placeholder=".crt .cer .pem"
              extensions={['.crt', '.cer', '.pem']}
              clearable
              searchable
              {...form.getInputProps('ssl_certfile')}
              value={form.getValues().ssl_certfile ?? null}
              onChange={(value) =>
                form.setFieldValue('ssl_certfile', value ?? undefined)
              }
            />
            <ProjectFileSelect
              label={
                <LabelWithTooltip
                  label="Client key"
                  tooltip="Path to client certificate key file"
                />
              }
              placeholder=".crt .cer .pem .key"
              extensions={['.crt', '.cer', '.pem', '.key']}
              clearable
              searchable
              {...form.getInputProps('ssl_keyfile')}
              value={form.getValues().ssl_keyfile ?? null}
              onChange={(value) =>
                form.setFieldValue('ssl_keyfile', value ?? undefined)
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
