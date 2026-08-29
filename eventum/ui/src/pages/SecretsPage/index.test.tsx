import { ModalsProvider } from '@mantine/modals';
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import SecretsPage from './index';
import * as secretHooks from '@/api/hooks/useSecrets';
import { renderWithProviders } from '@/test/render';

vi.mock('@/api/hooks/useSecrets');

const mutation = () => ({ mutate: vi.fn(), isPending: false });

// The value of a secret is read only when the row asks for it.
let fetchSecretValue: ReturnType<typeof vi.fn>;

function setup(names: string[] | null = ['git_token'], state = {}) {
  vi.mocked(secretHooks.useSecretNames).mockReturnValue({
    data: names ?? undefined,
    isLoading: false,
    isError: false,
    error: null,
    isSuccess: names !== null,
    ...state,
  } as unknown as ReturnType<typeof secretHooks.useSecretNames>);

  renderWithProviders(
    <ModalsProvider>
      <SecretsPage />
    </ModalsProvider>
  );
}

beforeEach(() => {
  vi.clearAllMocks();

  fetchSecretValue = vi
    .fn()
    .mockResolvedValue({ data: 'token', isSuccess: true });

  vi.mocked(secretHooks.useSecretValue).mockReturnValue({
    data: undefined,
    refetch: fetchSecretValue,
    isLoading: false,
  } as unknown as ReturnType<typeof secretHooks.useSecretValue>);

  vi.mocked(secretHooks.useSecretReferences).mockReturnValue({
    data: [],
    isLoading: false,
  } as unknown as ReturnType<typeof secretHooks.useSecretReferences>);

  for (const name of Object.keys(secretHooks)) {
    if (name.endsWith('Mutation')) {
      vi.mocked(
        secretHooks[name as keyof typeof secretHooks] as () => unknown
      ).mockReturnValue(mutation());
    }
  }
});

/**
 * A secret value must never be on screen unless the user asked for it,
 * and the mask must not give its length away either - the list is
 * readable by anyone who can see the screen.
 */
describe('SecretsPage', () => {
  it('lists the secrets the keyring holds', () => {
    setup(['git_token', 'opensearch_password']);

    expect(screen.getByText('git_token')).toBeInTheDocument();
    expect(screen.getByText('opensearch_password')).toBeInTheDocument();
  });

  it('counts them', () => {
    setup(['git_token', 'opensearch_password']);

    expect(screen.getByText('2 secrets')).toBeInTheDocument();
  });

  it('counts a single secret in the singular', () => {
    setup(['git_token']);

    expect(screen.getByText('1 secret')).toBeInTheDocument();
  });

  it('masks every value it lists', () => {
    setup(['git_token']);

    expect(screen.getByText('••••••••')).toBeInTheDocument();
    expect(screen.queryByText('token')).not.toBeInTheDocument();
  });

  it('masks values of the same length whatever they hold', () => {
    setup(['a', 'b']);

    const masks = screen.getAllByText('••••••••');

    expect(masks).toHaveLength(2);
  });

  it('offers to add the first secret when there are none', () => {
    setup([]);

    expect(screen.getByText('No secrets yet')).toBeInTheDocument();
  });

  it('opens the form for a new secret', async () => {
    const user = userEvent.setup();
    setup([]);

    await user.click(screen.getByRole('button', { name: /Add secret/ }));

    expect(screen.getByRole('textbox', { name: /Name/ })).toBeInTheDocument();
  });

  it('waits while the list is being read', () => {
    setup(null, { isLoading: true, isSuccess: false });

    expect(screen.queryByRole('table')).not.toBeInTheDocument();
  });

  it('reports a failure to read it', () => {
    setup(null, {
      isLoading: false,
      isSuccess: false,
      isError: true,
      error: new Error('keyring locked'),
    });

    expect(
      screen.getByText('Failed to load list of secrets')
    ).toBeInTheDocument();
    expect(screen.getByText(/keyring locked/)).toBeInTheDocument();
  });

  it('says how a secret is referenced from a configuration', () => {
    setup(['git_token']);

    expect(screen.getByText('${secrets.name}')).toBeInTheDocument();
  });

  it('reveals a value only when asked', async () => {
    const user = userEvent.setup();
    setup(['git_token']);

    const row = screen.getByRole('row', { name: /git_token/ });
    const reveal = within(row)
      .getAllByRole('button')
      .find((button) => button.getAttribute('title')?.match(/show/i));

    expect(reveal).toBeDefined();
    expect(screen.queryByText('token')).not.toBeInTheDocument();

    await user.click(reveal!);

    // The value is fetched on demand and only then shown, so both have
    // to happen for the reveal to be working.
    expect(fetchSecretValue).toHaveBeenCalledTimes(1);
    expect(await screen.findByText('token')).toBeInTheDocument();
  });
});
