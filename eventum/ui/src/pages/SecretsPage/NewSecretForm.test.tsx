import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { NewSecretForm } from './NewSecretForm';
import { SECRET_NAME_ERROR } from '@/api/routes/secrets/schemas';
import { renderWithProviders } from '@/test/render';

const setSecretMock = vi.hoisted(() => vi.fn());

vi.mock('@/api/hooks/useSecrets', () => ({
  useSetSecretValueMutation: () => ({
    mutate: setSecretMock,
    isPending: false,
  }),
}));

async function fill(name: string) {
  renderWithProviders(<NewSecretForm onCancel={vi.fn()} />);

  await userEvent.type(screen.getByLabelText('Name'), name);
  await userEvent.type(screen.getByLabelText('Value'), 'value');
  await userEvent.click(screen.getByText('Add'));
}

describe('NewSecretForm', () => {
  it('adds a secret under a name a configuration can reference', async () => {
    setSecretMock.mockClear();

    await fill('opensearch_password');

    expect(setSecretMock).toHaveBeenCalledWith(
      expect.objectContaining({ name: 'opensearch_password' }),
      expect.anything()
    );
  });

  it.each(['my-secret', '1secret', 'my key', 'a}b', 'API_TOKEN'])(
    'refuses %s, which no configuration could reference',
    async (name) => {
      setSecretMock.mockClear();

      await fill(name);

      expect(await screen.findByText(SECRET_NAME_ERROR)).toBeVisible();
      expect(setSecretMock).not.toHaveBeenCalled();
    }
  );
});
