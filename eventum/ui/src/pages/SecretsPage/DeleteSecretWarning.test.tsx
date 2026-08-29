import { screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { DeleteSecretWarning } from './DeleteSecretWarning';
import { useSecretReferences } from '@/api/hooks/useSecrets';
import { SecretReferences } from '@/api/routes/secrets/schemas';
import { renderWithProviders } from '@/test/render';

vi.mock('@/api/hooks/useSecrets', () => ({
  useSecretReferences: vi.fn(),
}));

const mockedReferences = vi.mocked(useSecretReferences);

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

function renderWarning(): void {
  renderWithProviders(<DeleteSecretWarning secretName="git_token" />);
}

describe('DeleteSecretWarning', () => {
  beforeEach(() => {
    mockedReferences.mockReset();
  });

  it('asks for the referrers of the secret being deleted', () => {
    const data: SecretReferences = { projects: [], repositories: [] };
    mockedReferences.mockReturnValue(references({ data }));

    renderWarning();

    expect(mockedReferences).toHaveBeenCalledWith('git_token', true);
  });

  it('states that the removal is what happens either way', () => {
    const data: SecretReferences = { projects: [], repositories: [] };
    mockedReferences.mockReturnValue(references({ data }));

    renderWarning();

    expect(screen.getByText(/will be deleted from keyring/)).toBeVisible();
    expect(screen.getByText('Nothing reads this secret.')).toBeVisible();
  });

  it('names what each kind of referrer is about to lose', () => {
    const data: SecretReferences = {
      projects: ['web-nginx'],
      repositories: ['internal-packs'],
    };
    mockedReferences.mockReturnValue(references({ data }));

    renderWarning();

    expect(screen.getByText('web-nginx')).toBeVisible();
    expect(screen.getByText(/fail to load until/)).toBeVisible();
    expect(screen.getByText('internal-packs')).toBeVisible();
    expect(screen.getByText(/stop answering until/)).toBeVisible();
  });

  it('claims nothing while the answer is still on its way', () => {
    mockedReferences.mockReturnValue(references());

    renderWarning();

    expect(screen.queryByText('Nothing reads this secret.')).toBeNull();
    expect(screen.getByText(/will be deleted from keyring/)).toBeVisible();
  });

  it('warns instead of claiming nothing when the check fails', () => {
    mockedReferences.mockReturnValue(
      references({ isError: true, error: new Error('boom') })
    );

    renderWarning();

    expect(screen.getByText('Cannot tell what uses this secret')).toBeVisible();
    expect(screen.queryByText('Nothing reads this secret.')).toBeNull();
  });
});
