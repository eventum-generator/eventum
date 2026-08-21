import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { RenameSecretModal } from './RenameSecretModal';
import {
  useRenameSecretMutation,
  useSecretReferences,
} from '@/api/hooks/useSecrets';
import { SecretReferences } from '@/api/routes/secrets/schemas';
import { renderWithProviders } from '@/test/render';
import { showSuccessNotification } from '@/utils/notifications';

vi.mock('@/api/hooks/useSecrets', () => ({
  useSecretReferences: vi.fn(),
  useRenameSecretMutation: vi.fn(),
}));

vi.mock('@/utils/notifications', () => ({
  showSuccessNotification: vi.fn(),
  showErrorNotification: vi.fn(),
}));

const mockedReferences = vi.mocked(useSecretReferences);
const mockedRename = vi.mocked(useRenameSecretMutation);

type ReferencesResult = ReturnType<typeof useSecretReferences>;

function references(
  overrides: Partial<ReferencesResult> = {}
): ReferencesResult {
  return {
    data: undefined,
    isLoading: false,
    isError: false,
    error: null,
    ...overrides,
  } as ReferencesResult;
}

const mutate = vi.fn();

interface MutateHandlers {
  onSuccess: (repointed: string[]) => void;
}

/** The options the component passed to the mutation on the one call. */
function handlersOfTheCall(): MutateHandlers {
  const call = mutate.mock.calls[0];
  if (call === undefined) {
    throw new Error('the mutation was never called');
  }

  return call[1] as MutateHandlers;
}

/** The variables the component passed to the mutation. */
function variablesOfTheCall(): unknown {
  const call = mutate.mock.calls[0];
  if (call === undefined) {
    throw new Error('the mutation was never called');
  }

  return call[0];
}

function renderModal(): void {
  renderWithProviders(
    <RenameSecretModal secretName="git_token" existingSecretNames={[]} />
  );
}

describe('RenameSecretModal', () => {
  beforeEach(() => {
    mutate.mockReset();
    mockedRename.mockReturnValue({
      mutate,
      isPending: false,
    } as unknown as ReturnType<typeof useRenameSecretMutation>);
  });

  it('asks for the referrers of the secret being renamed', () => {
    const data: SecretReferences = { projects: [], repositories: [] };
    mockedReferences.mockReturnValue(references({ data }));

    renderModal();

    expect(mockedReferences).toHaveBeenCalledWith('git_token', true);
  });

  it('names the projects that keep the old placeholder', () => {
    const data: SecretReferences = {
      projects: ['web-nginx'],
      repositories: [],
    };
    mockedReferences.mockReturnValue(references({ data }));

    renderModal();

    expect(screen.getByText('web-nginx')).toBeInTheDocument();
    expect(screen.getByText(/Update the placeholder/)).toBeInTheDocument();
  });

  it('names the repositories that are repointed', () => {
    const data: SecretReferences = {
      projects: [],
      repositories: ['internal'],
    };
    mockedReferences.mockReturnValue(references({ data }));

    renderModal();

    expect(screen.getByText('internal')).toBeInTheDocument();
    expect(screen.getByText(/repointed at the new name/)).toBeInTheDocument();
  });

  it('reports both kinds apart when both refer to the secret', () => {
    const data: SecretReferences = {
      projects: ['web-nginx'],
      repositories: ['internal'],
    };
    mockedReferences.mockReturnValue(references({ data }));

    renderModal();

    expect(screen.getByText(/Update the placeholder/)).toBeInTheDocument();
    expect(screen.getByText(/repointed at the new name/)).toBeInTheDocument();
  });

  it('states that nothing reads a secret without referrers', () => {
    const data: SecretReferences = { projects: [], repositories: [] };
    mockedReferences.mockReturnValue(references({ data }));

    renderModal();

    expect(screen.getByText('Nothing reads this secret.')).toBeInTheDocument();
  });

  it('claims nothing only once the answer is in', () => {
    mockedReferences.mockReturnValue(references());

    renderModal();

    expect(screen.queryByText('Nothing reads this secret.')).toBeNull();
  });

  it('warns instead of claiming nothing reads it when the check fails', () => {
    mockedReferences.mockReturnValue(
      references({ isError: true, error: new Error('boom') })
    );

    renderModal();

    expect(
      screen.getByText('Cannot tell what uses this secret')
    ).toBeInTheDocument();
    expect(screen.queryByText('Nothing reads this secret.')).toBeNull();
  });
});

describe('RenameSecretModal renaming', () => {
  beforeEach(() => {
    mutate.mockReset();
    mockedRename.mockReturnValue({
      mutate,
      isPending: false,
    } as unknown as ReturnType<typeof useRenameSecretMutation>);
    const data: SecretReferences = { projects: [], repositories: [] };
    mockedReferences.mockReturnValue(references({ data }));
    vi.mocked(showSuccessNotification).mockReset();
  });

  it('renames the secret the dialog was opened for', async () => {
    const user = userEvent.setup();
    renderModal();

    const input = screen.getByLabelText(/New secret name/);
    await user.clear(input);
    await user.type(input, 'forge_token');
    await user.click(screen.getByRole('button', { name: 'Rename' }));

    expect(mutate).toHaveBeenCalledTimes(1);
    expect(variablesOfTheCall()).toEqual({
      name: 'git_token',
      newName: 'forge_token',
    });
  });

  it('names the repointed repositories once the rename lands', async () => {
    const user = userEvent.setup();
    renderModal();

    const input = screen.getByLabelText(/New secret name/);
    await user.clear(input);
    await user.type(input, 'forge_token');
    await user.click(screen.getByRole('button', { name: 'Rename' }));

    handlersOfTheCall().onSuccess(['internal', 'mirror']);

    expect(showSuccessNotification).toHaveBeenCalledWith(
      'Renamed',
      'Secret "git_token" renamed to "forge_token", ' +
        'internal, mirror repointed at it'
    );
  });

  it('keeps the message plain when no repository held the secret', async () => {
    const user = userEvent.setup();
    renderModal();

    const input = screen.getByLabelText(/New secret name/);
    await user.clear(input);
    await user.type(input, 'forge_token');
    await user.click(screen.getByRole('button', { name: 'Rename' }));

    handlersOfTheCall().onSuccess([]);

    expect(showSuccessNotification).toHaveBeenCalledWith(
      'Renamed',
      'Secret "git_token" renamed to "forge_token"'
    );
  });
});
