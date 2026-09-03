import {
  Group,
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
import { S3EncoderParams } from './components/S3EncoderParams';
import {
  ADDRESSING_STYLES,
  S3OutputPluginConfig,
  S3OutputPluginConfigSchema,
} from '@/api/routes/generator-configs/schemas/plugins/output/configs/s3';
import { LabelWithTooltip } from '@/components/ui/LabelWithTooltip';
import { SecretPasswordInput } from '@/components/ui/SecretPasswordInput';
import { useOpenSecretsPage } from '@/utils/useOpenSecretsPage';

interface S3OutputPluginParamsProps {
  initialConfig: S3OutputPluginConfig;
  onChange: (config: S3OutputPluginConfig) => void;
}

export const S3OutputPluginParams: FC<S3OutputPluginParamsProps> = ({
  initialConfig,
  onChange,
}) => {
  const openSecretsPage = useOpenSecretsPage();
  const form = useForm<S3OutputPluginConfig>({
    initialValues: initialConfig,
    validate: zod4Resolver(S3OutputPluginConfigSchema),
    onValuesChange: onChange,
    validateInputOnChange: true,
  });

  return (
    <Stack gap="xs">
      <TextInput
        label={
          <LabelWithTooltip
            label="Bucket"
            tooltip="Name of the bucket to write objects to"
          />
        }
        required
        {...form.getInputProps('bucket')}
        onChange={(event) =>
          form.setFieldValue(
            'bucket',
            event.currentTarget.value !== ''
              ? event.currentTarget.value
              : undefined!
          )
        }
      />

      <TextInput
        label={
          <LabelWithTooltip
            label="Key template"
            tooltip="Template of object keys, substitutes `year`, `month`, `day`,
            `hour`, `minute`, `second` and `timestamp` of the moment the object
            is written at in UTC, `seq` with the number of objects written
            before it, `uuid` with a random value and `ext` with the extension
            of the selected encoding"
          />
        }
        placeholder="year={year}/month={month}/day={day}/hour={hour}/{timestamp}-{uuid}{ext}"
        {...form.getInputProps('key_template')}
        onChange={(event) =>
          form.setFieldValue(
            'key_template',
            event.currentTarget.value !== ''
              ? event.currentTarget.value
              : undefined
          )
        }
      />

      <Group grow wrap="nowrap" align="start">
        <TextInput
          label={
            <LabelWithTooltip
              label="Endpoint URL"
              tooltip="Address of the storage endpoint, the AWS endpoint of the
              selected region is used when not set"
            />
          }
          placeholder="URL"
          {...form.getInputProps('endpoint_url')}
          onChange={(event) =>
            form.setFieldValue(
              'endpoint_url',
              event.currentTarget.value !== ''
                ? event.currentTarget.value
                : undefined
            )
          }
        />
        <TextInput
          label={
            <LabelWithTooltip label="Region" tooltip="Region of the bucket" />
          }
          placeholder="us-east-1"
          {...form.getInputProps('region')}
          onChange={(event) =>
            form.setFieldValue(
              'region',
              event.currentTarget.value !== ''
                ? event.currentTarget.value
                : undefined
            )
          }
        />
      </Group>

      <Select
        label={
          <LabelWithTooltip
            label="Addressing style"
            tooltip="Whether the bucket name goes into the path of a request or
            into its host name, `auto` picks path style for a custom endpoint
            and virtual hosted style for AWS"
          />
        }
        data={[...ADDRESSING_STYLES]}
        value={
          typeof form.values.addressing_style === 'string'
            ? form.values.addressing_style
            : 'auto'
        }
        onChange={(value) =>
          form.setFieldValue(
            'addressing_style',
            (value as (typeof ADDRESSING_STYLES)[number]) ?? undefined
          )
        }
      />

      <Paper withBorder p="xs">
        <Stack gap="xs">
          <Text size="sm" fw="bold">
            Credentials
          </Text>
          <Text size="xs" c="dimmed">
            Left empty, credentials are resolved from the environment.
          </Text>

          <Group grow wrap="nowrap" align="start">
            <TextInput
              label={
                <LabelWithTooltip
                  label="Access key ID"
                  tooltip="Access key ID to authenticate with"
                />
              }
              {...form.getInputProps('access_key_id')}
              onChange={(event) =>
                form.setFieldValue(
                  'access_key_id',
                  event.currentTarget.value !== ''
                    ? event.currentTarget.value
                    : undefined
                )
              }
            />
            <SecretPasswordInput
              onOpenSecrets={openSecretsPage}
              label={
                <LabelWithTooltip
                  label="Secret access key"
                  tooltip="Secret access key to authenticate with"
                />
              }
              {...form.getInputProps('secret_access_key')}
              onChange={(value) =>
                form.setFieldValue(
                  'secret_access_key',
                  value !== '' ? value : undefined
                )
              }
            />
          </Group>

          <SecretPasswordInput
            onOpenSecrets={openSecretsPage}
            label={
              <LabelWithTooltip
                label="Session token"
                tooltip="Session token of temporary credentials"
              />
            }
            {...form.getInputProps('session_token')}
            onChange={(value) =>
              form.setFieldValue(
                'session_token',
                value !== '' ? value : undefined
              )
            }
          />
        </Stack>
      </Paper>

      <Paper withBorder p="xs">
        <Stack gap="xs">
          <Text size="sm" fw="bold">
            Objects
          </Text>
          <Text size="xs" c="dimmed">
            Every batch of events becomes one object, so their size follows the
            batch parameters of the generator.
          </Text>

          <S3EncoderParams
            value={form.getValues().encoder}
            onChange={(values) => form.setFieldValue('encoder', values)}
          />

          <TextInput
            label={
              <LabelWithTooltip
                label="Content type"
                tooltip="Content type to set on objects, the content type of the
                selected encoding is used when not set"
              />
            }
            placeholder="application/x-ndjson"
            {...form.getInputProps('content_type')}
            onChange={(event) =>
              form.setFieldValue(
                'content_type',
                event.currentTarget.value !== ''
                  ? event.currentTarget.value
                  : undefined
              )
            }
          />
        </Stack>
      </Paper>

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
        <NumberInput
          label={
            <LabelWithTooltip
              label="Max retries"
              tooltip="Maximum number of retries of a failed request, default
              value is 3"
            />
          }
          placeholder="number"
          min={0}
          step={1}
          allowDecimal={false}
          {...form.getInputProps('max_retries')}
          value={form.getValues().max_retries ?? ''}
          onChange={(value) =>
            form.setFieldValue(
              'max_retries',
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
                tooltip="Whether to verify SSL certificate of the storage
                endpoint"
              />
            }
            {...form.getInputProps('verify', { type: 'checkbox' })}
            checked={
              typeof form.values.verify === 'boolean'
                ? form.values.verify
                : true
            }
          />

          <ProjectFileSelect
            label={
              <LabelWithTooltip
                label="CA certificate"
                tooltip="CA certificate for verification of the storage endpoint"
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
          onChange={(event) =>
            form.setFieldValue(
              'proxy_url',
              event.currentTarget.value !== ''
                ? event.currentTarget.value
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
