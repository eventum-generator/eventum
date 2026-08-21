import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { RenameSecretModal } from './RenameSecretModal';
import { renderWithProviders } from '@/test/render';

const renameMock = vi.hoisted(() => vi.fn());

vi.mock('@/api/hooks/useSecrets', () => ({
  useRenameSecretMutation: () => ({ mutate: renameMock, isPending: false }),
  useSecretReferences: () => ({ data: [], isLoading: false }),
}));

async function renameTo(newName: string) {
  renderWithProviders(
    <RenameSecretModal secretName="api_key" existingSecretNames={['api_key']} />
  );

  // The label carries the asterisk of a required field, so it is
  // matched by part of its text.
  const input = screen.getByLabelText(/New secret name/);
  await userEvent.clear(input);
  await userEvent.type(input, newName);
}

describe('RenameSecretModal', () => {
  it('renames to a name a configuration can reference', async () => {
    renameMock.mockClear();

    await renameTo('api_token');
    await userEvent.click(screen.getByText('Rename'));

    expect(renameMock).toHaveBeenCalledWith(
      { name: 'api_key', newName: 'api_token' },
      expect.anything()
    );
  });

  it('refuses a name no configuration could reference', async () => {
    renameMock.mockClear();

    await renameTo('api-token');

    expect(
      await screen.findByText(
        'Only letters, digits and "_" are allowed, separated by "."'
      )
    ).toBeVisible();
    expect(renameMock).not.toHaveBeenCalled();
  });
});
