import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ScenariosCard } from './ScenariosCard';
import {
  useAddGeneratorToScenarioMutation,
  useRemoveGeneratorFromScenarioMutation,
} from '@/api/hooks/useScenarios';
import { renderWithProviders } from '@/test/render';

vi.mock('@/api/hooks/useScenarios');

const add = { mutate: vi.fn(), isPending: false };
const remove = { mutate: vi.fn(), isPending: false };

function setup(
  options: { memberScenarios?: string[]; allScenarios?: string[] } = {}
) {
  vi.mocked(useAddGeneratorToScenarioMutation).mockReturnValue(add as never);
  vi.mocked(useRemoveGeneratorFromScenarioMutation).mockReturnValue(
    remove as never
  );

  renderWithProviders(
    <MemoryRouter>
      <ScenariosCard
        instanceId="web"
        memberScenarios={options.memberScenarios ?? []}
        allScenarios={options.allScenarios ?? ['nightly', 'smoke']}
      />
    </MemoryRouter>
  );

  return { user: userEvent.setup() };
}

beforeEach(() => {
  vi.clearAllMocks();
});

/**
 * Membership is startup state shared with the scenarios themselves, so
 * it is written the moment it is changed rather than on the save of the
 * settings form beside it. An instance can be in a scenario once, so the
 * menu offers only the scenarios it is not in.
 */
describe('ScenariosCard', () => {
  it('says an instance belongs to nothing yet', () => {
    setup({ memberScenarios: [] });

    expect(screen.getByText('Not part of any scenario.')).toBeInTheDocument();
  });

  it('lists the scenarios the instance is in, each linked', () => {
    setup({ memberScenarios: ['nightly'] });

    expect(screen.getByRole('link', { name: 'nightly' })).toHaveAttribute(
      'href',
      '/scenarios/nightly'
    );
  });

  it('offers the scenarios the instance is not in', async () => {
    const { user } = setup({ memberScenarios: ['nightly'] });

    await user.click(screen.getByRole('button', { name: /Add to scenario/ }));

    expect(
      await screen.findByRole('menuitem', { name: 'smoke' })
    ).toBeInTheDocument();
    expect(screen.queryByRole('menuitem', { name: 'nightly' })).toBeNull();
  });

  it('offers no add when the instance is in every scenario', () => {
    setup({ memberScenarios: ['nightly', 'smoke'] });

    expect(
      screen.getByRole('button', { name: /Add to scenario/ })
    ).toBeDisabled();
  });

  it('joins the scenario that was picked', async () => {
    const { user } = setup();

    await user.click(screen.getByRole('button', { name: /Add to scenario/ }));
    await user.click(await screen.findByRole('menuitem', { name: 'nightly' }));

    expect(add.mutate).toHaveBeenCalledWith(
      { name: 'nightly', generatorId: 'web' },
      expect.anything()
    );
  });

  it('leaves the scenario a row is removed from', async () => {
    const { user } = setup({ memberScenarios: ['nightly'] });

    await user.click(
      screen.getByRole('button', { name: 'Remove from scenario' })
    );

    expect(remove.mutate).toHaveBeenCalledWith(
      { name: 'nightly', generatorId: 'web' },
      expect.anything()
    );
  });
});
