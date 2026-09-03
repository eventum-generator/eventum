import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { AuthParams } from './AuthParams';
import { useSecretNames } from '@/api/hooks/useSecrets';
import {
  AuthType,
  HTTPAuthConfig,
} from '@/api/routes/generator-configs/schemas/plugins/output/auth';
import { renderWithProviders } from '@/test/render';

vi.mock('@/api/hooks/useSecrets');

function setup(value?: HTTPAuthConfig) {
  vi.mocked(useSecretNames).mockReturnValue({
    data: ['api_token'],
    isLoading: false,
    isError: false,
    isSuccess: true,
    error: null,
  } as unknown as ReturnType<typeof useSecretNames>);

  const onChange = vi.fn();

  renderWithProviders(
    <MemoryRouter>
      <AuthParams value={value} onChange={onChange} />
    </MemoryRouter>
  );

  return { onChange, user: userEvent.setup() };
}

/** Pick a method from the list the select offers. */
async function pickMethod(
  user: ReturnType<typeof userEvent.setup>,
  method: string
) {
  await user.click(screen.getByRole('textbox', { name: /Method/ }));

  const option = [
    ...document.querySelectorAll<HTMLElement>('[role="option"]'),
  ].find((candidate) => candidate.textContent === method);

  await user.click(option!);
}

beforeEach(() => {
  vi.clearAllMocks();
});

/**
 * Each method of authentication carries its own credentials, and those
 * only make sense under the method they belong to. Switching the method
 * therefore replaces the whole section instead of adding to it, and a
 * credential of the previous method must not travel to the backend
 * under a method that has no field for it.
 */
describe('AuthParams', () => {
  it('offers every method the plugin supports', async () => {
    const { user } = setup();

    await user.click(screen.getByRole('textbox', { name: /Method/ }));

    expect(
      [...document.querySelectorAll('[role="option"]')].map(
        (option) => option.textContent
      )
    ).toEqual(['basic', 'bearer', 'oauth2_client_credentials']);
  });

  it('offers nothing but the method until one is picked', () => {
    setup();

    expect(screen.getByRole('textbox', { name: /Method/ })).toBeVisible();
    expect(screen.queryByRole('textbox', { name: /Username/ })).toBeNull();
    expect(screen.queryByLabelText(/Token URL/)).toBeNull();
  });

  it('starts a picked method from its own empty credentials', async () => {
    const { user, onChange } = setup();

    await pickMethod(user, 'bearer');

    expect(onChange).toHaveBeenCalledWith({
      type: AuthType.Bearer,
      token: '',
    });
  });

  it('replaces the section when the method changes', async () => {
    const { user, onChange } = setup({
      type: AuthType.Basic,
      username: 'user',
      password: 'pass',
    });

    await pickMethod(user, 'oauth2_client_credentials');

    expect(onChange).toHaveBeenCalledWith({
      type: AuthType.OAuth2ClientCredentials,
      token_url: '',
      client_id: '',
      client_secret: '',
    });
  });

  it('drops the section when the method is cleared', async () => {
    const { user, onChange } = setup({
      type: AuthType.Bearer,
      token: 'abc',
    });

    const clear = document.querySelector<HTMLElement>(
      '.mantine-Select-section button, .mantine-CloseButton-root'
    );
    await user.click(clear!);

    expect(onChange).toHaveBeenCalledWith(undefined);
  });

  it('takes the credentials of basic authentication', async () => {
    const { user, onChange } = setup({
      type: AuthType.Basic,
      username: '',
    });

    await user.click(screen.getByRole('textbox', { name: /Username/ }));
    await user.paste('user');

    expect(onChange).toHaveBeenCalledWith({
      type: AuthType.Basic,
      username: 'user',
    });
  });

  it('offers the parameters of the grant for oauth2 only', () => {
    setup({
      type: AuthType.OAuth2ClientCredentials,
      token_url: 'https://login.example.com/token',
      client_id: 'id',
      client_secret: 'secret',
    });

    expect(screen.getByRole('textbox', { name: /Token URL/ })).toBeVisible();
    expect(screen.getByRole('textbox', { name: /Client ID/ })).toBeVisible();
    expect(screen.getByRole('textbox', { name: /Scopes/ })).toBeVisible();
    expect(screen.getByRole('textbox', { name: /Audience/ })).toBeVisible();
    expect(screen.queryByRole('textbox', { name: /Username/ })).toBeNull();
  });

  it('splits the scopes written as one line', async () => {
    const { user, onChange } = setup({
      type: AuthType.OAuth2ClientCredentials,
      token_url: 'https://login.example.com/token',
      client_id: 'id',
      client_secret: 'secret',
    });

    await user.click(screen.getByRole('textbox', { name: /Scopes/ }));
    await user.paste('openid profile');

    expect(onChange).toHaveBeenCalledWith({
      type: AuthType.OAuth2ClientCredentials,
      token_url: 'https://login.example.com/token',
      client_id: 'id',
      client_secret: 'secret',
      scopes: ['openid', 'profile'],
    });
  });

  it('leaves the scopes unset when the line is emptied', async () => {
    const { user, onChange } = setup({
      type: AuthType.OAuth2ClientCredentials,
      token_url: 'https://login.example.com/token',
      client_id: 'id',
      client_secret: 'secret',
      scopes: ['openid'],
    });

    await user.clear(screen.getByRole('textbox', { name: /Scopes/ }));

    expect(onChange).toHaveBeenCalledWith({
      type: AuthType.OAuth2ClientCredentials,
      token_url: 'https://login.example.com/token',
      client_id: 'id',
      client_secret: 'secret',
      scopes: undefined,
    });
  });
});

describe('AuthParams credentials', () => {
  it('offers the keyring on every field that holds a credential', async () => {
    const { user } = setup({
      type: AuthType.OAuth2ClientCredentials,
      token_url: 'https://login.example.com/token',
      client_id: 'id',
      client_secret: 'secret',
    });

    // one picker per credential the grant carries: the client secret
    const pickers = screen.getAllByRole('button', {
      name: 'Use a keyring secret',
    });
    expect(pickers).toHaveLength(1);

    await user.click(pickers[0]!);

    expect(await screen.findByText('api_token')).toBeVisible();
  });

  it('states which credential is still missing', () => {
    setup({ type: AuthType.Bearer, token: '' });

    expect(screen.getByText('Token is required')).toBeVisible();
  });

  it('reports the method the client credentials are presented with', async () => {
    const { user, onChange } = setup({
      type: AuthType.OAuth2ClientCredentials,
      token_url: 'https://login.example.com/token',
      client_id: 'id',
      client_secret: 'secret',
    });

    const select = screen.getByRole('textbox', { name: /Client auth method/ });
    await user.click(select);

    // `basic` is also a method of authentication, so the option is
    // taken from the dropdown of this select rather than the document
    const dropdown = document.querySelector<HTMLElement>(
      `#${select.getAttribute('aria-controls')}`
    )!;
    const option = [
      ...dropdown.querySelectorAll<HTMLElement>('[role="option"]'),
    ].find((candidate) => candidate.textContent === 'basic');
    await user.click(option!);

    expect(onChange).toHaveBeenCalledWith({
      type: AuthType.OAuth2ClientCredentials,
      token_url: 'https://login.example.com/token',
      client_id: 'id',
      client_secret: 'secret',
      client_auth_method: 'basic',
    });
  });

  it('takes the extra form parameters of the grant', async () => {
    const { user, onChange } = setup({
      type: AuthType.OAuth2ClientCredentials,
      token_url: 'https://login.example.com/token',
      client_id: 'id',
      client_secret: 'secret',
    });

    await user.click(screen.getByRole('textbox', { name: /Extra parameters/ }));
    await user.paste('{"tenant": "contoso"}');

    expect(onChange).toHaveBeenCalledWith({
      type: AuthType.OAuth2ClientCredentials,
      token_url: 'https://login.example.com/token',
      client_id: 'id',
      client_secret: 'secret',
      extra_params: { tenant: 'contoso' },
    });
  });

  it('takes the resource the token is requested for', async () => {
    const { user, onChange } = setup({
      type: AuthType.OAuth2ClientCredentials,
      token_url: 'https://login.example.com/token',
      client_id: 'id',
      client_secret: 'secret',
    });

    await user.click(screen.getByRole('textbox', { name: /Resource/ }));
    await user.paste('https://monitor.azure.com/');

    expect(onChange).toHaveBeenCalledWith({
      type: AuthType.OAuth2ClientCredentials,
      token_url: 'https://login.example.com/token',
      client_id: 'id',
      client_secret: 'secret',
      resource: 'https://monitor.azure.com/',
    });
  });
});

describe('AuthParams feedback', () => {
  it.each([
    [AuthType.Basic, { type: AuthType.Basic, username: '' }],
    [AuthType.Bearer, { type: AuthType.Bearer, token: '' }],
  ] as [AuthType, HTTPAuthConfig][])(
    'offers the keyring on the credential of %s',
    (_type, config) => {
      setup(config);

      expect(
        screen.getAllByRole('button', { name: 'Use a keyring secret' })
      ).toHaveLength(1);
    }
  );

  it.each([
    ['Username is required', { type: AuthType.Basic, username: '' }],
    [
      'Token URL is required',
      {
        type: AuthType.OAuth2ClientCredentials,
        token_url: '',
        client_id: 'id',
        client_secret: 'secret',
      },
    ],
    [
      'Client ID is required',
      {
        type: AuthType.OAuth2ClientCredentials,
        token_url: 'https://login.example.com/token',
        client_id: '',
        client_secret: 'secret',
      },
    ],
    [
      'Client secret is required',
      {
        type: AuthType.OAuth2ClientCredentials,
        token_url: 'https://login.example.com/token',
        client_id: 'id',
        client_secret: '',
      },
    ],
  ] as [string, HTTPAuthConfig][])('states that %s', (message, config) => {
    setup(config);

    expect(screen.getByText(message)).toBeVisible();
  });

  it('keeps the section while the extra parameters are unparsable', async () => {
    const { user, onChange } = setup({
      type: AuthType.OAuth2ClientCredentials,
      token_url: 'https://login.example.com/token',
      client_id: 'id',
      client_secret: 'secret',
    });

    await user.click(screen.getByRole('textbox', { name: /Extra parameters/ }));
    await user.paste('{"tenant":');

    // half written JSON says nothing about what the parameters are
    expect(onChange).not.toHaveBeenCalled();
  });

  it('drops the extra parameters when they are emptied', async () => {
    const { user, onChange } = setup({
      type: AuthType.OAuth2ClientCredentials,
      token_url: 'https://login.example.com/token',
      client_id: 'id',
      client_secret: 'secret',
      extra_params: { tenant: 'contoso' },
    });

    await user.clear(screen.getByRole('textbox', { name: /Extra parameters/ }));

    expect(onChange).toHaveBeenCalledWith({
      type: AuthType.OAuth2ClientCredentials,
      token_url: 'https://login.example.com/token',
      client_id: 'id',
      client_secret: 'secret',
      extra_params: undefined,
    });
  });
});
