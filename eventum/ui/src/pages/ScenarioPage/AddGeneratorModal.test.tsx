import { ModalsProvider } from '@mantine/modals';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { AddGeneratorModal } from './AddGeneratorModal';
import { useAddGeneratorToScenarioMutation } from '@/api/hooks/useScenarios';
import { useStartupGenerators } from '@/api/hooks/useStartup';
import { StartupGeneratorParameters } from '@/api/routes/startup/schemas';
import { renderWithProviders } from '@/test/render';

vi.mock('@/api/hooks/useScenarios');
vi.mock('@/api/hooks/useStartup');

function entry(
  id: string,
  scenarios: string[] = []
): StartupGeneratorParameters {
  return {
    id,
    path: `${id}/generator.yml`,
    scenarios,
  } as StartupGeneratorParameters;
}

type Handlers = { onSuccess?: () => void; onError?: (e: unknown) => void };

interface Options {
  entries?: StartupGeneratorParameters[];
  isLoading?: boolean;
  isError?: boolean;
  fail?: boolean;
}

function setup(options: Options = {}) {
  const mutate = vi.fn((_args: unknown, handlers: Handlers = {}): void => {
    if (options.fail === true) {
      handlers.onError?.(new Error('already there'));
    } else {
      handlers.onSuccess?.();
    }
  });

  vi.mocked(useAddGeneratorToScenarioMutation).mockReturnValue({
    mutate,
    isPending: false,
  } as never);
  vi.mocked(useStartupGenerators).mockReturnValue({
    data: options.entries ?? [entry('web'), entry('api')],
    isLoading: options.isLoading ?? false,
    isError: options.isError ?? false,
    isSuccess: options.isLoading !== true && options.isError !== true,
    error: options.isError === true ? new Error('no startup') : null,
  } as unknown as ReturnType<typeof useStartupGenerators>);

  renderWithProviders(
    <ModalsProvider>
      <AddGeneratorModal scenarioName="nightly" />
    </ModalsProvider>
  );

  return { mutate, user: userEvent.setup() };
}

/** The options the instance picker offers. */
function options(): string[] {
  return [...document.querySelectorAll('[role="option"]')].map(
    (option) => option.textContent ?? ''
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

/**
 * A scenario groups instances, and an instance can only be in it once -
 * so the picker offers what is not in it yet, and nothing else. Offering
 * an instance already in the scenario would send a request the backend
 * refuses.
 */
describe('AddGeneratorModal', () => {
  it('offers the instances that are not in the scenario', async () => {
    const { user } = setup({
      entries: [entry('web'), entry('api', ['nightly'])],
    });

    await user.click(screen.getByRole('textbox', { name: /Instance/ }));

    expect(options()).toEqual(['web']);
  });

  it('adds the instance that was picked to this scenario', async () => {
    const { user, mutate } = setup();

    await user.click(screen.getByRole('textbox', { name: /Instance/ }));

    // The options of a Mantine picker are drawn in a portal that the
    // accessible tree does not reach, so the one to click is found in
    // the document.
    const option = [
      ...document.querySelectorAll<HTMLElement>('[role="option"]'),
    ].find((candidate) => candidate.textContent === 'api');
    await user.click(option!);

    await user.click(screen.getByRole('button', { name: /Add/ }));

    expect(mutate).toHaveBeenCalledWith(
      { name: 'nightly', generatorId: 'api' },
      expect.anything()
    );
  });

  it('offers no add until an instance is picked', () => {
    setup();

    expect(screen.getByRole('button', { name: /Add/ })).toBeDisabled();
  });

  it('says nothing is left to add', async () => {
    const { user } = setup({ entries: [entry('web', ['nightly'])] });

    await user.click(screen.getByRole('textbox', { name: /Instance/ }));

    expect(options()).toEqual([]);
  });

  it('waits rather than offering an empty picker', () => {
    setup({ isLoading: true });

    expect(screen.queryByRole('textbox', { name: /Instance/ })).toBeNull();
  });

  it('reports the instances it could not read', () => {
    setup({ isError: true });

    expect(screen.getByText('Failed to load instances')).toBeInTheDocument();
  });
});
