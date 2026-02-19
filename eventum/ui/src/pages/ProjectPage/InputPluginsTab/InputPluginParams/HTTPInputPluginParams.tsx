import { Group, NumberInput, Stack, TagsInput, TextInput } from '@mantine/core';
import { useForm } from '@mantine/form';
import { zod4Resolver } from 'mantine-form-zod-resolver';
import { FC } from 'react';
import validator from 'validator';
import z from 'zod';

import {
  HTTPInputPluginConfig,
  HTTPInputPluginConfigSchema,
} from '@/api/routes/generator-configs/schemas/plugins/input/configs/http';
import { LabelWithTooltip } from '@/components/ui/LabelWithTooltip';

interface HTTPInputPluginParamsProps {
  initialConfig: HTTPInputPluginConfig;
  onChange: (config: HTTPInputPluginConfig) => void;
}

const HostSchema = z
  .string()
  .optional()
  .refine(
    (value) => {
      if (!value) {
        return true;
      }

      return (
        validator.isIP(value) ||
        validator.isFQDN(value, {
          require_tld: false,
          allow_underscores: true,
        })
      );
    },
    { message: 'Invalid IP or hostname' }
  );

const ExtendedHTTPInputPluginConfigSchema = HTTPInputPluginConfigSchema.extend({
  host: HostSchema,
});

export const HTTPInputPluginParams: FC<HTTPInputPluginParamsProps> = ({
  initialConfig,
  onChange,
}) => {
  const form = useForm<HTTPInputPluginConfig>({
    initialValues: initialConfig,
    onValuesChange: onChange,
    validate: zod4Resolver(ExtendedHTTPInputPluginConfigSchema),
    onSubmitPreventDefault: 'always',
    validateInputOnChange: true,
  });

  return (
    <Stack gap="xs">
      <Group grow align="start">
        <TextInput
          label={
            <LabelWithTooltip
              label="Host"
              tooltip="Bind address. Default values is 0.0.0.0 (i.e. all interfaces are listened)"
            />
          }
          placeholder="ip or hostname"
          {...form.getInputProps('host')}
          onChange={(value) =>
            form.setFieldValue(
              'host',
              value.currentTarget.value !== ''
                ? value.currentTarget.value
                : undefined
            )
          }
        />
        <NumberInput
          label={<LabelWithTooltip label="Port" tooltip="Bind port" />}
          min={1}
          max={65_535}
          step={1}
          allowDecimal={false}
          required
          {...form.getInputProps('port')}
          value={form.getValues().port ?? ''}
          onChange={(value) =>
            form.setFieldValue(
              'port',
              typeof value === 'number' ? value : undefined!
            )
          }
        />
      </Group>
      <NumberInput
        label={
          <LabelWithTooltip
            label="Max pending requests"
            tooltip="Maximum number of incoming requests to store in queue before they are processed. If a request is received and the queue is full a 429 response will be returned immediately. Default value is 100."
          />
        }
        min={1}
        step={1}
        allowDecimal={false}
        {...form.getInputProps('max_pending_requests')}
        value={form.getValues().max_pending_requests ?? ''}
        onChange={(value) =>
          form.setFieldValue(
            'max_pending_requests',
            typeof value === 'number' ? value : undefined
          )
        }
      />
      <TagsInput
        label={
          <LabelWithTooltip
            label="Tags"
            tooltip="Tags list attached to an input plugin"
          />
        }
        placeholder="Press Enter to submit a tag"
        {...form.getInputProps('tags')}
        value={form.getValues().tags ?? []}
        onChange={(value) =>
          form.setFieldValue('tags', value.length > 0 ? value : undefined)
        }
      />
    </Stack>
  );
};
