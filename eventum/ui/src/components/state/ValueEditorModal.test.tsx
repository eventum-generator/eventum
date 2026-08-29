import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { ValueEditorModal } from './ValueEditorModal';
import { renderWithProviders } from '@/test/render';

interface Options {
  opened?: boolean;
  keyName?: string;
  value?: unknown;
}

function setup(options: Options = {}) {
  const onSave = vi.fn();
  const onClose = vi.fn();

  const view = renderWithProviders(
    <ValueEditorModal
      opened={options.opened ?? true}
      onClose={onClose}
      keyName={options.keyName ?? 'session'}
      value={'value' in options ? options.value : { id: 7 }}
      onSave={onSave}
    />
  );

  return { ...view, onSave, onClose, user: userEvent.setup() };
}

/** The editable area of the editor. */
function editor(): HTMLElement {
  const content = document.querySelector<HTMLElement>('.cm-content');

  if (content === null) {
    throw new Error('the editor is not drawn');
  }

  return content;
}

/**
 * A value of the state is any JSON, so it is edited as text and has to
 * be parsed back before it can be stored. Text that is not JSON must
 * neither be stored nor be silently dropped: the editor says so and
 * holds the save until it parses.
 */
describe('ValueEditorModal', () => {
  it('opens on the value it was given, formatted', () => {
    setup({ value: { id: 7 } });

    expect(editor()).toHaveTextContent('"id": 7');
  });

  it('names the key being edited', () => {
    setup({ keyName: 'fleet' });

    expect(screen.getByText('fleet')).toBeInTheDocument();
  });

  it('stores what was typed, parsed, under the same key', async () => {
    const { user, onSave, onClose } = setup({ value: 1 });

    await user.click(editor());
    await user.keyboard('{Control>}a{/Control}');
    await user.paste('{"id": 8}');
    await user.click(screen.getByRole('button', { name: 'Save' }));

    expect(onSave).toHaveBeenCalledWith('session', { id: 8 });
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('reports text that is not JSON rather than storing it', async () => {
    const { user, onSave } = setup({ value: 1 });

    await user.click(editor());
    await user.keyboard('{Control>}a{/Control}');
    await user.paste('{"id":');

    await waitFor(() =>
      expect(screen.getByText('Invalid JSON')).toBeInTheDocument()
    );
    expect(screen.getByRole('button', { name: 'Save' })).toBeDisabled();
    expect(onSave).not.toHaveBeenCalled();
  });

  it('takes a value that is not an object', async () => {
    const { user, onSave } = setup({ value: 1 });

    await user.click(editor());
    await user.keyboard('{Control>}a{/Control}');
    await user.paste('"a string"');
    await user.click(screen.getByRole('button', { name: 'Save' }));

    expect(onSave).toHaveBeenCalledWith('session', 'a string');
  });

  it('leaves the value alone when the editing is cancelled', async () => {
    const { user, onSave, onClose } = setup();

    await user.click(screen.getByRole('button', { name: 'Cancel' }));

    expect(onSave).not.toHaveBeenCalled();
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('draws nothing while it is closed', () => {
    setup({ opened: false });

    expect(screen.queryByRole('button', { name: 'Save' })).toBeNull();
  });
});
