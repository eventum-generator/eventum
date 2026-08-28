import { useForm } from '@mantine/form';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { FC } from 'react';
import { describe, expect, it } from 'vitest';

import { TimePatternForm } from './TimePatternForm';
import {
  Distribution,
  TimePatternConfig,
} from '@/api/routes/generator-configs/schemas/plugins/input/configs/time_patterns';
import { ProjectNameProvider } from '@/pages/ProjectPage/context/ProjectNameContext';
import { renderWithProviders } from '@/test/render';

const PATTERN: TimePatternConfig = {
  label: 'business hours',
  oscillator: {
    period: 1,
    unit: 'hours',
    start: 'now',
    end: 'never',
  },
  multiplier: { ratio: 100 },
  randomizer: { deviation: 0.3, direction: 'mixed', sampling: 1024 },
  spreader: { distribution: Distribution.BETA, parameters: { a: 15, b: 15 } },
};

/** Mount the form over a real form, the way the pattern editor does. */
const Host: FC<{
  initial?: Partial<TimePatternConfig>;
  onValues?: (values: TimePatternConfig) => void;
}> = ({ initial, onValues }) => {
  const form = useForm<TimePatternConfig>({
    mode: 'uncontrolled',
    initialValues: { ...PATTERN, ...initial },
  });

  // The oscillator draws a versatile datetime field, which reaches for
  // the project it belongs to.
  return (
    <ProjectNameProvider initialProjectName="web">
      <TimePatternForm form={form} />
      <button type="button" onClick={() => onValues?.(form.getValues())}>
        read values
      </button>
    </ProjectNameProvider>
  );
};

/**
 * A field of the form, by the label beside it.
 *
 * "Period" names both the duration and its unit, so the whole name is
 * matched rather than any part of it.
 */
function field(label: string): HTMLElement {
  return screen.getByRole('textbox', { name: new RegExp(`^${label}$`) });
}

async function readValues(
  user: ReturnType<typeof userEvent.setup>
): Promise<void> {
  await user.click(screen.getByRole('button', { name: 'read values' }));
}

/**
 * A time pattern is the one input configuration that is not a plugin
 * config but a file of its own, and the form is the only editor for it.
 * The distribution at the bottom decides which parameters the pattern
 * carries at all, so switching it has to seed the ones the new shape
 * needs - a pattern left with the parameters of the previous shape is
 * one the backend refuses.
 */
describe('TimePatternForm', () => {
  it('opens on the whole pattern', () => {
    renderWithProviders(<Host />);

    expect(field('Label')).toHaveValue('business hours');
    expect(field('Period')).toHaveValue('1');
    expect(field('Ratio')).toHaveValue('100');
    expect(field('Deviation')).toHaveValue('0.3');
    expect(field('Sampling')).toHaveValue('1024');
  });

  it('reports an edit of the oscillator upwards', async () => {
    const user = userEvent.setup();
    let values: TimePatternConfig | undefined;

    renderWithProviders(
      <Host
        onValues={(v) => {
          values = v;
        }}
      />
    );

    // The field cannot hold nothing - emptying it writes a zero - so the
    // edit is typed onto the value it opened with.
    await user.click(field('Period'));
    await user.keyboard('{End}4');
    await readValues(user);

    expect(values?.oscillator.period).toBe(14);
  });

  it('draws the parameters of the beta distribution it opens on', () => {
    renderWithProviders(<Host />);

    expect(field('Alpha')).toHaveValue('15');
    expect(field('Beta')).toHaveValue('15');
  });

  it.each([
    ['Triangular', Distribution.TRIANGULAR, { left: 0, mode: 0.5, right: 1 }],
    ['Uniform', Distribution.UNIFORM, { low: 0, high: 1 }],
    ['Beta', Distribution.BETA, { a: 15, b: 15 }],
  ])(
    'seeds the parameters %s needs when it is picked',
    async (label, distribution, parameters) => {
      const user = userEvent.setup();
      let values: TimePatternConfig | undefined;

      renderWithProviders(
        <Host
          initial={
            label === 'Beta'
              ? {
                  spreader: {
                    distribution: Distribution.UNIFORM,
                    parameters: { low: 0, high: 1 },
                  },
                }
              : undefined
          }
          onValues={(v) => {
            values = v;
          }}
        />
      );

      await user.click(screen.getByText(label));
      await readValues(user);

      expect(values?.spreader.distribution).toBe(distribution);
      expect(values?.spreader.parameters).toEqual(
        expect.objectContaining(parameters)
      );
    }
  );

  it('drops the beta parameters from the form once another shape is picked', async () => {
    const user = userEvent.setup();

    renderWithProviders(<Host />);

    await user.click(screen.getByText('Uniform'));

    // The fields of the previous shape are gone rather than left behind
    // holding values nothing reads.
    expect(screen.queryByRole('textbox', { name: /Alpha/ })).toBeNull();
    expect(screen.queryByRole('textbox', { name: /Beta/ })).toBeNull();
  });

  it('offers a direction for the deviation of every period', async () => {
    const user = userEvent.setup();
    let values: TimePatternConfig | undefined;

    renderWithProviders(
      <Host
        onValues={(v) => {
          values = v;
        }}
      />
    );

    await user.click(screen.getByText('Increase'));
    await readValues(user);

    expect(values?.randomizer.direction).toBe('increase');
  });
});
