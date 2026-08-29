import { useForm } from '@mantine/form';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { FC } from 'react';
import { describe, expect, it } from 'vitest';

import { GenerationParametersSection } from './index';
import { GenerationParameters } from '@/api/routes/instance/schemas';
import { renderWithProviders } from '@/test/render';

/**
 * The section is mounted the way both pages mount it: over a form that
 * was initialised with what the backend reported.
 */
const Host: FC<{
  initial: GenerationParameters;
  liveMode?: boolean;
  onValues?: (values: GenerationParameters) => void;
}> = ({ initial, liveMode, onValues }) => {
  const form = useForm<GenerationParameters>({
    mode: 'uncontrolled',
    initialValues: initial,
  });

  onValues?.(form.getValues());

  return (
    <>
      <GenerationParametersSection form={form} liveMode={liveMode} />
      <button type="button" onClick={() => onValues?.(form.getValues())}>
        read values
      </button>
    </>
  );
};

/** A switch of the section, addressed by the label beside it. */
function switchOf(label: string): HTMLElement {
  return screen.getByRole('switch', { name: new RegExp(label) });
}

/**
 * A numeric field of the section. The label carries a help button of
 * its own, so the field is reached by its accessible name rather than
 * by the label text, which two elements answer to.
 */
function fieldOf(label: string): HTMLElement {
  return screen.getByRole('textbox', { name: new RegExp(label) });
}

/**
 * Two of these controls carry a state the backend spells as null - a
 * lifted queue limit and a batch formed by one condition alone - and an
 * unset field is not the same state: it leaves the backend on its own
 * default. So the section is read for what it shows for a null, and for
 * what it writes when the user switches the limit off.
 */
describe('GenerationParametersSection', () => {
  it('draws the byte limit as off when the instance has none', () => {
    renderWithProviders(
      <Host initial={{ queue: { max_event_bytes: null } }} />
    );

    expect(switchOf('Limit memory of events queue')).not.toBeChecked();
  });

  it('draws the byte limit as on when the instance leaves it unset', () => {
    // An unset limit is the default one, which is a limit.
    renderWithProviders(<Host initial={{ queue: {} }} />);

    expect(switchOf('Limit memory of events queue')).toBeChecked();
  });

  it('lifts the limit with a null rather than by clearing the field', async () => {
    const user = userEvent.setup();
    let values: GenerationParameters = {};

    renderWithProviders(
      <Host
        initial={{ queue: { max_event_bytes: 268_435_456 } }}
        onValues={(v) => {
          values = v;
        }}
      />
    );

    await user.click(switchOf('Limit memory of events queue'));
    await user.click(screen.getByRole('button', { name: 'read values' }));

    expect(values.queue?.max_event_bytes).toBeNull();
  });

  it('disables the byte limit while it is lifted', async () => {
    const user = userEvent.setup();

    renderWithProviders(
      <Host initial={{ queue: { max_event_bytes: 268_435_456 } }} />
    );

    await user.click(switchOf('Limit memory of events queue'));

    expect(fieldOf('Maximum event bytes')).toBeDisabled();
  });

  it.each([
    ['size', { batch: { size: 10_000, delay: null } }, 'Batch delay'],
    ['delay', { batch: { size: null, delay: 1 } }, 'Batch size'],
  ])(
    'reads a batch formed by %s alone and disables the other condition',
    (_label, initial, disabled) => {
      renderWithProviders(<Host initial={initial as GenerationParameters} />);

      expect(fieldOf(disabled)).toBeDisabled();
    }
  );

  it('lifts a batch condition with a null when the mode drops it', async () => {
    const user = userEvent.setup();
    let values: GenerationParameters = {};

    renderWithProviders(
      <Host
        initial={{ batch: { size: 10_000, delay: 1 } }}
        onValues={(v) => {
          values = v;
        }}
      />
    );

    await user.click(screen.getByRole('radio', { name: 'Size' }));
    await user.click(screen.getByRole('button', { name: 'read values' }));

    expect(values.batch).toEqual({ size: 10_000, delay: null });
  });

  it('names what forms a batch in sample mode, where a delay does not', () => {
    renderWithProviders(
      <Host initial={{ batch: { size: 10_000, delay: 1 } }} liveMode={false} />
    );

    expect(
      screen.getByText(/batches are formed by size alone/)
    ).toBeInTheDocument();
  });

  it('says nothing about batching when only a size forms a batch', () => {
    renderWithProviders(<Host initial={{ batch: { size: 10_000 } }} />);

    expect(screen.queryByText(/formed by size alone/)).toBeNull();
  });
});
