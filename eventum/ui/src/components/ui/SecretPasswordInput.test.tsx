import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { describe, expect, it, vi } from 'vitest';

import { SecretPasswordInput } from './SecretPasswordInput';
import { renderWithProviders } from '@/test/render';

const useSecretNamesMock = vi.hoisted(() => vi.fn());

vi.mock('@/api/hooks/useSecrets', () => ({
  useSecretNames: useSecretNamesMock,
}));

interface FieldProps {
  readonly initial?: string;
  readonly onOpenSecrets?: () => void;
}

function Field({ initial = '', onOpenSecrets }: FieldProps) {
  const [value, setValue] = useState(initial);

  return (
    <SecretPasswordInput
      label="Password"
      value={value}
      onChange={setValue}
      onOpenSecrets={onOpenSecrets}
    />
  );
}

function input(): HTMLInputElement {
  return screen.getByLabelText('Password');
}

describe('SecretPasswordInput', () => {
  it('writes the reference of the secret picked from the dropdown', async () => {
    useSecretNamesMock.mockReturnValue({ data: ['git_token', 'api_key'] });
    renderWithProviders(<Field />);

    await userEvent.click(screen.getByLabelText('Use a keyring secret'));
    await userEvent.click(await screen.findByText('api_key'));

    expect(input().value).toBe('${secrets.api_key}');
  });

  it('keeps a typed value as it is typed', async () => {
    useSecretNamesMock.mockReturnValue({ data: ['git_token'] });
    renderWithProviders(<Field />);

    await userEvent.type(input(), 'ghp_token');

    expect(input().value).toBe('ghp_token');
  });

  it('hides a value that carries the credential', () => {
    useSecretNamesMock.mockReturnValue({ data: [] });
    renderWithProviders(<Field initial="ghp_token" />);

    expect(input().type).toBe('password');
  });

  it('hides a reference padded with spaces, which is not one', () => {
    useSecretNamesMock.mockReturnValue({ data: ['git_token'] });
    renderWithProviders(<Field initial="${secrets.git_token} " />);

    // The backend substitutes inside the padding and authenticates
    // with it, so the field must not present this as a reference.
    expect(input().type).toBe('password');
  });

  it('shows a value that only names a secret', () => {
    useSecretNamesMock.mockReturnValue({ data: ['git_token'] });
    renderWithProviders(<Field initial="${secrets.git_token}" />);

    // Nothing is behind the mask, so no control offers to lift it.
    expect(input().type).toBe('text');
    expect(screen.queryByLabelText('Show the password')).toBeNull();
  });

  it('reveals a carried credential on request', async () => {
    useSecretNamesMock.mockReturnValue({ data: [] });
    renderWithProviders(<Field initial="ghp_token" />);

    await userEvent.click(screen.getByLabelText('Show the password'));

    expect(input().type).toBe('text');
  });

  it('states an empty keyring instead of an empty dropdown', async () => {
    useSecretNamesMock.mockReturnValue({ data: [] });
    renderWithProviders(<Field />);

    await userEvent.click(screen.getByLabelText('Use a keyring secret'));

    expect(
      await screen.findByText('The keyring holds no secrets yet')
    ).toBeInTheDocument();
  });

  it('offers the page secrets are managed on', async () => {
    useSecretNamesMock.mockReturnValue({ data: [] });
    const onOpenSecrets = vi.fn();
    renderWithProviders(<Field onOpenSecrets={onOpenSecrets} />);

    await userEvent.click(screen.getByLabelText('Use a keyring secret'));
    await userEvent.click(await screen.findByText('Manage secrets'));

    expect(onOpenSecrets).toHaveBeenCalledOnce();
  });

  it('leaves a name that cannot be written as a reference unpicked', async () => {
    useSecretNamesMock.mockReturnValue({ data: ['my key'] });
    renderWithProviders(<Field />);

    await userEvent.click(screen.getByLabelText('Use a keyring secret'));
    await userEvent.click(await screen.findByText('my key'));

    expect(input().value).toBe('');
  });

  it('holds no search over a keyring short enough to read', async () => {
    useSecretNamesMock.mockReturnValue({ data: ['git_token', 'api_key'] });
    renderWithProviders(<Field />);

    await userEvent.click(screen.getByLabelText('Use a keyring secret'));
    await screen.findByText('git_token');

    expect(screen.queryByPlaceholderText('Search secrets')).toBeNull();
  });

  it('says when the search matches no secret', async () => {
    const names = Array.from({ length: 12 }, (_, index) => `secret_${index}`);
    useSecretNamesMock.mockReturnValue({ data: names });
    renderWithProviders(<Field />);

    await userEvent.click(screen.getByLabelText('Use a keyring secret'));
    await userEvent.type(
      await screen.findByPlaceholderText('Search secrets'),
      'absent'
    );

    expect(await screen.findByText('No secret of that name')).toBeVisible();
  });

  it('searches a keyring too long to read through', async () => {
    const names = Array.from({ length: 12 }, (_, index) => `secret_${index}`);
    useSecretNamesMock.mockReturnValue({ data: names });
    renderWithProviders(<Field />);

    await userEvent.click(screen.getByLabelText('Use a keyring secret'));
    await userEvent.type(
      await screen.findByPlaceholderText('Search secrets'),
      'secret_11'
    );

    expect(screen.getByText('secret_11')).toBeInTheDocument();
    expect(screen.queryByText('secret_10')).toBeNull();
  });
});
