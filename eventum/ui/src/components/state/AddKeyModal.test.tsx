import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { AddKeyModal } from './AddKeyModal';
import { renderWithProviders } from '@/test/render';

function setup(existingKeys: string[] = []) {
  const onAdd = vi.fn();
  const onClose = vi.fn();

  const { rerender } = renderWithProviders(
    <AddKeyModal
      opened
      onClose={onClose}
      existingKeys={existingKeys}
      onAdd={onAdd}
    />
  );

  return { onAdd, onClose, rerender };
}

function keyField(): HTMLElement {
  return screen.getByRole('textbox', { name: 'Key' });
}

function valueField(): HTMLElement {
  return screen.getByRole('textbox', { name: 'Value' });
}

/**
 * A key added here goes straight into the state of a running generator,
 * so the value has to be valid JSON and the key has to be new: adding
 * an existing one would silently replace what a template put there.
 */
describe('AddKeyModal', () => {
  it('opens on an empty key and an empty string value', () => {
    setup();

    expect(keyField()).toHaveValue('');
    expect(valueField()).toHaveValue('""');
  });

  it('offers no adding until a key is given', () => {
    setup();

    expect(screen.getByRole('button', { name: 'Add' })).toBeDisabled();
  });

  it('adds the key with the value it was given', async () => {
    const user = userEvent.setup();
    const { onAdd, onClose } = setup();

    await user.type(keyField(), 'counter');
    await user.clear(valueField());
    await user.type(valueField(), '42');
    await user.click(screen.getByRole('button', { name: 'Add' }));

    expect(onAdd).toHaveBeenCalledWith('counter', 42);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('keeps the shape of a value that is not a scalar', async () => {
    const user = userEvent.setup();
    const { onAdd } = setup();

    await user.type(keyField(), 'hosts');
    await user.clear(valueField());
    await user.type(valueField(), '[[1,2]');
    await user.click(screen.getByRole('button', { name: 'Add' }));

    expect(onAdd).toHaveBeenCalledWith('hosts', [1, 2]);
  });

  it('refuses a key the state already holds', async () => {
    const user = userEvent.setup();
    const { onAdd } = setup(['counter']);

    await user.type(keyField(), 'counter');

    expect(await screen.findByText('Key already exists')).toBeVisible();
    expect(screen.getByRole('button', { name: 'Add' })).toBeDisabled();
    expect(onAdd).not.toHaveBeenCalled();
  });

  it('trims the key before comparing it', async () => {
    const user = userEvent.setup();
    setup(['counter']);

    await user.type(keyField(), '  counter  ');

    expect(await screen.findByText('Key already exists')).toBeVisible();
  });

  it('trims the key it adds', async () => {
    const user = userEvent.setup();
    const { onAdd } = setup();

    await user.type(keyField(), '  counter  ');
    await user.click(screen.getByRole('button', { name: 'Add' }));

    expect(onAdd).toHaveBeenCalledWith('counter', '');
  });

  it('refuses a key of only whitespace', async () => {
    const user = userEvent.setup();
    setup();

    await user.type(keyField(), '   ');

    expect(await screen.findByText('Key is required')).toBeVisible();
    expect(screen.getByRole('button', { name: 'Add' })).toBeDisabled();
  });

  it('refuses a value that is not JSON', async () => {
    const user = userEvent.setup();
    const { onAdd } = setup();

    await user.type(keyField(), 'counter');
    await user.clear(valueField());
    await user.type(valueField(), '{{oops');

    expect(await screen.findByText('Invalid JSON')).toBeVisible();
    expect(screen.getByRole('button', { name: 'Add' })).toBeDisabled();
    expect(onAdd).not.toHaveBeenCalled();
  });

  it('adds nothing when dismissed', async () => {
    const user = userEvent.setup();
    const { onAdd, onClose } = setup();

    await user.type(keyField(), 'counter');
    await user.click(screen.getByRole('button', { name: 'Cancel' }));

    expect(onAdd).not.toHaveBeenCalled();
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('starts clean each time it is opened', async () => {
    const user = userEvent.setup();
    const onAdd = vi.fn();
    const onClose = vi.fn();

    const { rerender } = renderWithProviders(
      <AddKeyModal opened onClose={onClose} existingKeys={[]} onAdd={onAdd} />
    );

    await user.type(keyField(), 'counter');

    rerender(
      <AddKeyModal
        opened={false}
        onClose={onClose}
        existingKeys={[]}
        onAdd={onAdd}
      />
    );
    rerender(
      <AddKeyModal opened onClose={onClose} existingKeys={[]} onAdd={onAdd} />
    );

    expect(keyField()).toHaveValue('');
  });
});
