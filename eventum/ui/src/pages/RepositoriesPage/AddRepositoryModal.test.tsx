import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { AddRepositoryModal } from './AddRepositoryModal';
import { APIError } from '@/api/errors';
import { useAddRepositoryMutation } from '@/api/hooks/useRepositories';
import { useSecretNames } from '@/api/hooks/useSecrets';
import { renderWithProviders } from '@/test/render';

vi.mock('@/api/hooks/useRepositories');
vi.mock('@/api/hooks/useSecrets');

interface Handlers {
  onSuccess?: () => void;
  onError?: (error: unknown) => void;
}

interface Options {
  existingNames?: string[];
  prefilled?: { name: string; url: string };
  error?: unknown;
}

function setup(options: Options = {}) {
  const mutate = vi.fn((_args: unknown, handlers: Handlers = {}): void => {
    if (options.error === undefined) {
      handlers.onSuccess?.();
    } else {
      handlers.onError?.(options.error);
    }
  });

  vi.mocked(useAddRepositoryMutation).mockReturnValue({
    mutate,
    isPending: false,
  } as never);
  vi.mocked(useSecretNames).mockReturnValue({
    data: ['github-token'],
  } as never);

  renderWithProviders(
    <AddRepositoryModal
      existingNames={options.existingNames ?? []}
      onOpenSecrets={vi.fn()}
      prefilled={options.prefilled}
    />
  );

  return { mutate, user: userEvent.setup() };
}

function field(name: string): HTMLElement {
  return screen.getByRole('textbox', { name: new RegExp(`^${name}`) });
}

async function fillValid(user: ReturnType<typeof userEvent.setup>) {
  await user.clear(field('Name'));
  await user.type(field('Name'), 'content-packs');
  await user.clear(field('URL'));
  await user.type(field('URL'), 'https://example.com/repo.git');
}

beforeEach(() => {
  vi.clearAllMocks();
});

/**
 * A repository is fetched by the instance, so what this form accepts
 * decides what the instance will try to reach. The rules mirror what the
 * backend enforces - a name it can address a directory by, a URL it can
 * fetch, credentials kept out of that URL - so a value it would refuse
 * is named here as a field error rather than coming back as a 422.
 */
describe('AddRepositoryModal', () => {
  it('refuses a name that is not one the backend can address', async () => {
    const { user } = setup();

    await user.type(field('Name'), 'not a name');

    expect(
      await screen.findByText(
        'Only letters, digits and symbols "-", "_" and "." are allowed'
      )
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Connect' })).toBeDisabled();
  });

  it('refuses a name that is already connected', async () => {
    const { user } = setup({ existingNames: ['content-packs'] });

    await user.type(field('Name'), 'content-packs');

    expect(
      await screen.findByText('Repository with such name is already connected')
    ).toBeInTheDocument();
  });

  it.each([
    ['git@example.com:owner/repo.git', 'URL must start with'],
    ['https://user:pass@example.com/repo.git', 'Provide credentials as'],
  ])('refuses the address %s', async (url, message) => {
    const { user } = setup();

    await user.type(field('URL'), url);

    expect(await screen.findByText(new RegExp(message))).toBeInTheDocument();
  });

  it.each(['feature/..', 'main/', 'main.lock'])(
    'refuses %s as a branch or tag',
    async (ref) => {
      const { user } = setup();

      await user.type(field('Branch or tag'), ref);

      expect(
        await screen.findByText('Not a valid branch or tag name')
      ).toBeInTheDocument();
    }
  );

  it('takes an empty branch as the default one', async () => {
    const { user, mutate } = setup();

    await fillValid(user);
    await user.click(screen.getByRole('button', { name: 'Connect' }));

    expect(mutate).toHaveBeenCalledWith(
      {
        repository: expect.objectContaining({
          name: 'content-packs',
          url: 'https://example.com/repo.git',
          ref: undefined,
        }),
        verify: true,
      },
      expect.anything()
    );
  });

  it('checks that the repository answers before connecting it', async () => {
    const { user, mutate } = setup();

    await fillValid(user);
    await user.click(screen.getByRole('button', { name: 'Connect' }));

    expect(mutate.mock.calls[0]?.[0]).toMatchObject({ verify: true });
  });

  it('offers to connect a repository that did not answer anyway', async () => {
    const { user, mutate } = setup({
      error: new APIError({
        message: 'Bad gateway',
        details: 'host unreachable',
        response: { status: 502 } as never,
      }),
    });

    await fillValid(user);
    await user.click(screen.getByRole('button', { name: 'Connect' }));

    // A repository that is merely down is worth connecting - the
    // catalog is read again later.
    expect(
      await screen.findByText('The repository did not answer')
    ).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Connect anyway' }));

    expect(mutate.mock.calls[1]?.[0]).toMatchObject({ verify: false });
  });

  it('does not offer a retry for a request that was wrong', async () => {
    const { user } = setup({
      error: new APIError({
        message: 'Invalid payload',
        response: { status: 422 } as never,
      }),
    });

    await fillValid(user);
    await user.click(screen.getByRole('button', { name: 'Connect' }));

    // Sending the same payload again would fail the same way.
    await waitFor(() =>
      expect(
        screen.queryByRole('button', { name: 'Connect anyway' })
      ).toBeNull()
    );
  });

  it('opens on the repository it was asked to connect', () => {
    setup({
      prefilled: {
        name: 'content-packs',
        url: 'https://example.com/repo.git',
      },
    });

    expect(field('Name')).toHaveValue('content-packs');
    expect(field('URL')).toHaveValue('https://example.com/repo.git');
  });

  it('offers the secrets the keyring holds for a private repository', async () => {
    const { user } = setup();

    // The credential of a private repository is a password field that
    // can take a keyring secret instead of a typed value.
    await user.click(
      screen.getByRole('button', { name: 'Use a keyring secret' })
    );

    expect(
      await screen.findByRole('menuitem', { name: /github-token/ })
    ).toBeInTheDocument();
  });
});
