import {
  Alert,
  Box,
  Group,
  NumberInput,
  PasswordInput,
  Radio,
  Switch,
  Text,
  TextInput,
  Tooltip,
} from '@mantine/core';
import { UseFormReturnType } from '@mantine/form';
import { IconAlertTriangle, IconLockExclamation } from '@tabler/icons-react';
import { FC } from 'react';

import { ServerParameters } from '@/api/routes/instance/schemas';
import { LabelWithTooltip } from '@/components/ui/LabelWithTooltip';

interface ServerParametersSectionProps {
  form: UseFormReturnType<ServerParameters>;
}

export const ServerParametersSection: FC<ServerParametersSectionProps> = ({
  form,
}) => {
  return (
    <>
      <Group>
        <Switch
          label={
            <LabelWithTooltip
              label="Enable API"
              tooltip="Eventum API is used for external app control and for serving web interface"
            />
          }
          {...form.getInputProps('api_enabled', { type: 'checkbox' })}
          key={form.key('api_enabled')}
        />
        <Switch
          label={
            <LabelWithTooltip
              label="Enable web UI"
              tooltip="Whether to enable web interface service that you are currently use"
            />
          }
          {...form.getInputProps('ui_enabled', { type: 'checkbox' })}
          key={form.key('ui_enabled')}
        />
      </Group>

      <Alert
        variant="default"
        icon={<Box c="orange" component={IconAlertTriangle}></Box>}
        title="Disabling API"
        hidden={form.getValues().api_enabled}
      >
        Web interface will not be functional after disabling API.
      </Alert>
      <Group grow align="start">
        <TextInput
          label={
            <LabelWithTooltip
              label="Bind host"
              tooltip="Address of the interface that should be listened by server (e.g. 127.0.0.1 or 0.0.0.0)"
            />
          }
          placeholder="hostname or IP"
          disabled={
            !(
              form.getValues().api_enabled === true ||
              form.getValues().ui_enabled === true
            )
          }
          {...form.getInputProps('host')}
          key={form.key('host')}
        />
        <NumberInput
          label={
            <LabelWithTooltip
              label="Bind port"
              tooltip="Port that should be listened by server"
            />
          }
          placeholder="port number (1 - 65 535)"
          allowDecimal={false}
          min={1}
          max={65_535}
          disabled={
            !(
              form.getValues().api_enabled === true ||
              form.getValues().ui_enabled === true
            )
          }
          {...form.getInputProps('port')}
          key={form.key('port')}
        />
      </Group>

      <Text size="sm" fw="bold" mt="md">
        SSL
      </Text>
      <Switch
        label="Enable SSL"
        disabled={
          !(
            form.getValues().api_enabled === true ||
            form.getValues().ui_enabled === true
          )
        }
        {...form.getInputProps('ssl.enabled', {
          type: 'checkbox',
        })}
        key={form.key('ssl.enabled')}
      />
      <Radio.Group
        name="verifyMode"
        label="Client certificate verification mode"
        description="Select how the server verifies client certificates during TLS handshake"
        {...form.getInputProps('ssl.verify_mode')}
        key={form.key('ssl.verify_mode')}
      >
        <Group mt="xs">
          <Tooltip
            withArrow
            label="Clients are not required to present a certificate"
            position="bottom"
            offset={12}
            openDelay={200}
          >
            <Box>
              <Radio
                disabled={
                  !(
                    form.getValues().api_enabled === true ||
                    form.getValues().ui_enabled === true
                  ) || !form.getValues().ssl?.enabled
                }
                value="none"
                label="None"
              />
            </Box>
          </Tooltip>
          <Tooltip
            withArrow
            label="Client certificate is validated if provided, but not required"
            position="bottom"
            offset={12}
            openDelay={200}
          >
            <Box>
              <Radio
                disabled={
                  !(
                    form.getValues().api_enabled === true ||
                    form.getValues().ui_enabled === true
                  ) || !form.getValues().ssl?.enabled
                }
                value="optional"
                label="Optional"
              />
            </Box>
          </Tooltip>
          <Tooltip
            withArrow
            label="A valid client certificate is required for connection (mTLS)"
            position="bottom"
            offset={12}
            openDelay={200}
          >
            <Box>
              <Radio
                disabled={
                  !(
                    form.getValues().api_enabled === true ||
                    form.getValues().ui_enabled === true
                  ) || !form.getValues().ssl?.enabled
                }
                value="required"
                label="Required"
              />
            </Box>
          </Tooltip>
        </Group>
      </Radio.Group>
      <TextInput
        label={
          <LabelWithTooltip
            label="Path to CA certificate"
            tooltip="Absolute path to CA certificate of PEM format"
          />
        }
        placeholder="/path/to/ca-cert.pem"
        disabled={
          !(
            form.getValues().api_enabled === true ||
            form.getValues().ui_enabled === true
          ) || !form.getValues().ssl?.enabled
        }
        {...form.getInputProps('ssl.ca_cert')}
        key={form.key('ssl.ca_cert')}
      />
      <TextInput
        label={
          <LabelWithTooltip
            label="Path to server certificate"
            tooltip="Absolute path to server certificate of PEM format"
          />
        }
        placeholder="/path/to/cert.pem"
        disabled={
          !(
            form.getValues().api_enabled === true ||
            form.getValues().ui_enabled === true
          ) || !form.getValues().ssl?.enabled
        }
        {...form.getInputProps('ssl.cert')}
        key={form.key('ssl.cert')}
      />
      <TextInput
        label={
          <LabelWithTooltip
            label="Path to server certificate key"
            tooltip="Absolute path to server certificate key"
          />
        }
        placeholder="/path/to/key.pem"
        disabled={
          !(
            form.getValues().api_enabled === true ||
            form.getValues().ui_enabled === true
          ) || !form.getValues().ssl?.enabled
        }
        {...form.getInputProps('ssl.cert_key')}
        key={form.key('ssl.cert_key')}
      />

      <Text size="sm" fw="bold" mt="md">
        Authentication
      </Text>
      <Group grow align="start">
        <TextInput
          label={
            <LabelWithTooltip
              label="Username"
              tooltip="Username for basic authentication of API requests"
            />
          }
          disabled={
            !(
              form.getValues().api_enabled === true ||
              form.getValues().ui_enabled === true
            )
          }
          {...form.getInputProps('auth.user')}
          key={form.key('auth.user')}
        />
        <PasswordInput
          label={
            <LabelWithTooltip
              label="Password"
              tooltip="Password for username for basic authentication of API requests"
            />
          }
          disabled={
            !(
              form.getValues().api_enabled === true ||
              form.getValues().ui_enabled === true
            )
          }
          {...form.getInputProps('auth.password')}
          key={form.key('auth.password')}
        />
      </Group>
      <Alert
        variant="default"
        icon={<Box c="orange" component={IconLockExclamation} />}
        title="Security notification"
      >
        Username and password are parameters in configuration file that stored
        in <b>plain text</b>.
      </Alert>
    </>
  );
};
