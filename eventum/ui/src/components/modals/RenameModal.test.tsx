import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { RenameModal } from './RenameModal';
import { renderWithProviders } from '@/test/render';

const PATTERN = /^[A-Za-z_]\w*$/;

function renderModal(onRename: (name: string) => void) {
  renderWithProviders(
    <RenameModal
      label="New name"
      currentName="api_key"
      takenNames={['api_key', 'taken']}
      pattern={PATTERN}
      patternError="Only letters, digits and _"
      isPending={false}
      onRename={onRename}
    />
  );

  return screen.getByLabelText(/New name/);
}

describe('RenameModal', () => {
  it('renames to a name the pattern accepts', async () => {
    const onRename = vi.fn();
    const input = renderModal(onRename);

    await userEvent.clear(input);
    await userEvent.type(input, 'api_token');
    await userEvent.click(screen.getByText('Rename'));

    expect(onRename).toHaveBeenCalledWith('api_token');
  });

  it('refuses a name the pattern rejects', async () => {
    const onRename = vi.fn();
    const input = renderModal(onRename);

    await userEvent.clear(input);
    await userEvent.type(input, 'api-token');

    expect(await screen.findByText('Only letters, digits and _')).toBeVisible();
    await userEvent.click(screen.getByText('Rename'));
    expect(onRename).not.toHaveBeenCalled();
  });
});
