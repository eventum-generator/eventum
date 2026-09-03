import {
  Group,
  JsonInput,
  Select,
  Stack,
  Text,
  TextInput,
} from '@mantine/core';
import { FC } from 'react';

import {
  AuthType,
  CLIENT_AUTH_METHODS,
  HTTPAuthConfig,
} from '@/api/routes/generator-configs/schemas/plugins/output/auth';
import { LabelWithTooltip } from '@/components/ui/LabelWithTooltip';
import { SecretPasswordInput } from '@/components/ui/SecretPasswordInput';
import { useOpenSecretsPage } from '@/utils/useOpenSecretsPage';

interface AuthParamsProps {
  value: HTTPAuthConfig | undefined;
  onChange: (config: HTTPAuthConfig | undefined) => void;
}

const EMPTY_CONFIGS: Record<AuthType, HTTPAuthConfig> = {
  [AuthType.Basic]: { type: AuthType.Basic, username: '' },
  [AuthType.Bearer]: { type: AuthType.Bearer, token: '' },
  [AuthType.OAuth2ClientCredentials]: {
    type: AuthType.OAuth2ClientCredentials,
    token_url: '',
    client_id: '',
    client_secret: '',
  },
};

export const AuthParams: FC<AuthParamsProps> = ({ value, onChange }) => {
  const openSecretsPage = useOpenSecretsPage();

  return (
    <Stack gap="4px">
      <Text size="sm" fw="bold">
        Authentication
      </Text>

      <Select
        label={
          <LabelWithTooltip
            label="Method"
            tooltip="How requests to the endpoint are authenticated"
          />
        }
        placeholder="no authentication"
        data={[
          AuthType.Basic,
          AuthType.Bearer,
          AuthType.OAuth2ClientCredentials,
        ]}
        clearable
        value={value?.type ?? null}
        onChange={(type) =>
          onChange(type ? EMPTY_CONFIGS[type as AuthType] : undefined)
        }
      />

      {value?.type === AuthType.Basic && (
        <Group grow align="start" wrap="nowrap">
          <TextInput
            label={
              <LabelWithTooltip
                label="Username"
                tooltip="Username to authenticate with"
              />
            }
            required
            error={value.username === '' ? 'Username is required' : undefined}
            value={value.username}
            onChange={(event) =>
              onChange({ ...value, username: event.currentTarget.value })
            }
          />
          <SecretPasswordInput
            onOpenSecrets={openSecretsPage}
            label={
              <LabelWithTooltip
                label="Password"
                tooltip="Password of the user"
              />
            }
            value={value.password ?? ''}
            onChange={(password) =>
              onChange({ ...value, password: password || undefined })
            }
          />
        </Group>
      )}

      {value?.type === AuthType.Bearer && (
        <SecretPasswordInput
          onOpenSecrets={openSecretsPage}
          label={
            <LabelWithTooltip
              label="Token"
              tooltip="Token sent in the Authorization header of every request"
            />
          }
          required
          error={value.token === '' ? 'Token is required' : undefined}
          value={value.token}
          onChange={(token) => onChange({ ...value, token })}
        />
      )}

      {value?.type === AuthType.OAuth2ClientCredentials && (
        <Stack gap="4px">
          <TextInput
            label={
              <LabelWithTooltip
                label="Token URL"
                tooltip="URL of the token endpoint"
              />
            }
            required
            error={value.token_url === '' ? 'Token URL is required' : undefined}
            value={value.token_url}
            onChange={(event) =>
              onChange({ ...value, token_url: event.currentTarget.value })
            }
          />

          <Group grow align="start" wrap="nowrap">
            <TextInput
              label={
                <LabelWithTooltip
                  label="Client ID"
                  tooltip="Identifier of the client"
                />
              }
              required
              error={
                value.client_id === '' ? 'Client ID is required' : undefined
              }
              value={value.client_id}
              onChange={(event) =>
                onChange({ ...value, client_id: event.currentTarget.value })
              }
            />
            <SecretPasswordInput
              onOpenSecrets={openSecretsPage}
              label={
                <LabelWithTooltip
                  label="Client secret"
                  tooltip="Secret of the client"
                />
              }
              required
              error={
                value.client_secret === ''
                  ? 'Client secret is required'
                  : undefined
              }
              value={value.client_secret}
              onChange={(clientSecret) =>
                onChange({ ...value, client_secret: clientSecret })
              }
            />
          </Group>

          <Group grow align="start" wrap="nowrap">
            <Select
              label={
                <LabelWithTooltip
                  label="Client auth method"
                  tooltip="Whether client credentials are sent in the body of
                  the token request or in its Authorization header. Default
                  value is post"
                />
              }
              data={[...CLIENT_AUTH_METHODS]}
              clearable
              value={value.client_auth_method ?? null}
              onChange={(method) =>
                onChange({
                  ...value,
                  client_auth_method: method ?? undefined,
                })
              }
            />
            <TextInput
              label={
                <LabelWithTooltip
                  label="Scopes"
                  tooltip="Scopes requested for the token, separated by a
                  space"
                />
              }
              value={(value.scopes ?? []).join(' ')}
              onChange={(event) => {
                const scopes = event.currentTarget.value
                  .split(' ')
                  .filter((scope) => scope !== '');

                onChange({
                  ...value,
                  scopes: scopes.length > 0 ? scopes : undefined,
                });
              }}
            />
          </Group>

          <Group grow align="start" wrap="nowrap">
            <TextInput
              label={
                <LabelWithTooltip
                  label="Audience"
                  tooltip="Audience the token is requested for"
                />
              }
              value={value.audience ?? ''}
              onChange={(event) =>
                onChange({
                  ...value,
                  audience: event.currentTarget.value || undefined,
                })
              }
            />
            <TextInput
              label={
                <LabelWithTooltip
                  label="Resource"
                  tooltip="Resource the token is requested for"
                />
              }
              value={value.resource ?? ''}
              onChange={(event) =>
                onChange({
                  ...value,
                  resource: event.currentTarget.value || undefined,
                })
              }
            />
          </Group>

          <JsonInput
            label="Extra parameters"
            description="Additional form parameters of the token request"
            placeholder="{ ... }"
            validationError="Invalid JSON"
            minRows={2}
            autosize
            defaultValue={
              value.extra_params
                ? JSON.stringify(value.extra_params, undefined, 2)
                : ''
            }
            onChange={(written) => {
              if (!written) {
                onChange({ ...value, extra_params: undefined });
                return;
              }

              let parsed: unknown;
              try {
                parsed = JSON.parse(written);
              } catch {
                return;
              }

              if (typeof parsed === 'object' && parsed !== null) {
                onChange({
                  ...value,
                  extra_params: parsed as Record<string, string>,
                });
              }
            }}
          />
        </Stack>
      )}
    </Stack>
  );
};
