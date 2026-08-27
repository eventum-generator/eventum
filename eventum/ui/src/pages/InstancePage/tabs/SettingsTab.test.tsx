import { useForm } from '@mantine/form';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { FC } from 'react';
import { describe, expect, it } from 'vitest';

import { SettingsTab } from './SettingsTab';
import { StartupGeneratorParameters } from '@/api/routes/startup/schemas';
import { renderWithProviders } from '@/test/render';

const PARAMS = {
  id: 'web',
  path: 'web/generator.yml',
  live_mode: true,
  skip_past: true,
  autostart: false,
  scenarios: [],
  params: {},
} as StartupGeneratorParameters;

/** Mount the tab the way the instance page does: over its form. */
const Host: FC<{
  initial?: Partial<StartupGeneratorParameters>;
  onValues?: (values: StartupGeneratorParameters) => void;
}> = ({ initial, onValues }) => {
  const form = useForm<StartupGeneratorParameters>({
    mode: 'uncontrolled',
    initialValues: { ...PARAMS, ...initial },
  });

  return (
    <>
      <SettingsTab form={form} />
      <button type="button" onClick={() => onValues?.(form.getValues())}>
        read values
      </button>
    </>
  );
};

/**
 * The parameters field.
 *
 * It is the only multi-line input of the tab, which is what separates it
 * from the numeric fields of the generation section below.
 */
function paramsField(): HTMLElement {
  return screen.getByPlaceholderText('{ ... }');
}

async function readValues(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole('button', { name: 'read values' }));
}

/**
 * These are the settings one instance runs under, and two of them only
 * make sense together: skipping past timestamps is a live-mode notion,
 * so switching to sample mode has to say so rather than leave a toggle
 * that does nothing. The parameters field holds a JSON object, and one
 * that cannot be parsed must not reach the form as a value.
 */
describe('SettingsTab', () => {
  it('opens on the mode the instance runs in', () => {
    renderWithProviders(<Host />);

    expect(screen.getByRole('radio', { name: 'Live' })).toBeChecked();
    expect(
      screen.getByText(
        'Events are emitted at their timestamp moments, in real time.'
      )
    ).toBeInTheDocument();
  });

  it('reports the other mode when it is picked', async () => {
    const user = userEvent.setup();
    let values: StartupGeneratorParameters | undefined;

    renderWithProviders(
      <Host
        onValues={(v) => {
          values = v;
        }}
      />
    );

    await user.click(screen.getByText('Sample'));
    await readValues(user);

    expect(values?.live_mode).toBe(false);
    expect(
      screen.getByText(
        'All events are emitted at once, as fast as the pipeline allows.'
      )
    ).toBeInTheDocument();
  });

  it('holds the past-skip back in a mode that has no schedule', async () => {
    const user = userEvent.setup();

    renderWithProviders(<Host />);

    const skip = screen.getByRole('switch', { name: 'Skip past timestamps' });
    expect(skip).toBeEnabled();

    await user.click(screen.getByText('Sample'));

    // Sample mode emits everything at once, so there is no past to skip.
    expect(skip).toBeDisabled();
    expect(screen.getByText('Only applies in live mode.')).toBeInTheDocument();
  });

  it('reports the autostart it was switched to', async () => {
    const user = userEvent.setup();
    let values: StartupGeneratorParameters | undefined;

    renderWithProviders(
      <Host
        onValues={(v) => {
          values = v;
        }}
      />
    );

    await user.click(screen.getByRole('switch', { name: 'Autostart' }));
    await readValues(user);

    expect(values?.autostart).toBe(true);
  });

  it('opens on the parameters the instance was registered with', () => {
    renderWithProviders(<Host initial={{ params: { host: 'web-01' } }} />);

    expect(paramsField()).toHaveValue('{\n  "host": "web-01"\n}');
  });

  it('takes a parameters object as the object it is', async () => {
    const user = userEvent.setup();
    let values: StartupGeneratorParameters | undefined;

    renderWithProviders(
      <Host
        onValues={(v) => {
          values = v;
        }}
      />
    );

    await user.clear(paramsField());
    await user.click(paramsField());
    await user.paste('{"host":"web-02"}');
    await readValues(user);

    expect(values?.params).toEqual({ host: 'web-02' });
  });

  it('leaves the parameters alone while the text is not an object yet', async () => {
    const user = userEvent.setup();
    let values: StartupGeneratorParameters | undefined;

    renderWithProviders(
      <Host
        initial={{ params: { host: 'web-01' } }}
        onValues={(v) => {
          values = v;
        }}
      />
    );

    await user.click(paramsField());
    await user.paste('{"host":');
    await readValues(user);

    // A half-typed object is not a value, and writing it as one would
    // drop what the instance already runs with.
    expect(values?.params).toEqual({ host: 'web-01' });
  });

  it('reads an emptied field as no parameters at all', async () => {
    const user = userEvent.setup();
    let values: StartupGeneratorParameters | undefined;

    renderWithProviders(
      <Host
        initial={{ params: { host: 'web-01' } }}
        onValues={(v) => {
          values = v;
        }}
      />
    );

    await user.clear(paramsField());
    await readValues(user);

    expect(values?.params).toBeUndefined();
  });

  it('holds the generation defaults the instance inherits', () => {
    renderWithProviders(<Host />);

    expect(screen.getByText('Batching')).toBeInTheDocument();
    expect(
      screen.getByRole('switch', { name: /Keep events order/ })
    ).toBeInTheDocument();
  });

  it('names what forms a batch in the mode the instance runs in', () => {
    renderWithProviders(
      <Host initial={{ batch: { size: 10_000, delay: 1 } } as never} />
    );

    // The note belongs to the mode: in live mode a delay only bounds the
    // timestamps still ahead of real time.
    expect(
      screen.getByText(
        'Timestamps that have already passed are formed into batches by size alone.'
      )
    ).toBeInTheDocument();
  });
});
