import { ActionIcon } from '@mantine/core';
import { ModalsProvider } from '@mantine/modals';
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { RowActions } from './RowActions';
import * as generators from '@/api/hooks/useGenerators';
import * as scenarios from '@/api/hooks/useScenarios';
import { renderWithProviders } from '@/test/render';

vi.mock('@/api/hooks/useGenerators');
vi.mock('@/api/hooks/useScenarios');

const MUTATIONS = {
  start: { mutate: vi.fn(), isPending: false },
  stop: { mutate: vi.fn(), isPending: false },
  status: { mutate: vi.fn(), isPending: false },
  remove: { mutate: vi.fn(), isPending: false },
  rename: { mutate: vi.fn(), isPending: false },
};

interface Options {
  hasRunning?: boolean;
  hasInactive?: boolean;
  affected?: string[];
}

async function setup(options: Options = {}) {
  const { hasRunning = false, hasInactive = true, affected = [] } = options;

  vi.mocked(generators.useBulkStartGeneratorMutation).mockReturnValue(
    MUTATIONS.start as never
  );
  vi.mocked(generators.useBulkStopGeneratorMutation).mockReturnValue(
    MUTATIONS.stop as never
  );
  vi.mocked(generators.useUpdateGeneratorStatus).mockReturnValue(
    MUTATIONS.status as never
  );
  vi.mocked(scenarios.useDeleteScenarioMutation).mockReturnValue(
    MUTATIONS.remove as never
  );
  vi.mocked(scenarios.useRenameScenarioMutation).mockReturnValue(
    MUTATIONS.rename as never
  );
  vi.mocked(scenarios.useScenarios).mockReturnValue({
    data: { web: ['web-live'] },
  } as never);

  const user = userEvent.setup();

  renderWithProviders(
    <MemoryRouter>
      <ModalsProvider>
        <RowActions
          target={<ActionIcon aria-label="Scenario actions" />}
          scenarioName="web"
          generatorIds={['web-live', 'web-batch']}
          hasRunning={hasRunning}
          hasInactive={hasInactive}
          getAffectedScenarios={() => affected}
        />
      </ModalsProvider>
    </MemoryRouter>
  );

  await user.click(screen.getByRole('button', { name: 'Scenario actions' }));

  return user;
}

async function item(name: string): Promise<HTMLElement> {
  return await screen.findByRole('menuitem', { name });
}

beforeEach(() => {
  vi.clearAllMocks();
});

/**
 * A scenario acts on all of its instances at once, and an instance can
 * belong to more than one scenario. So stopping a scenario can stop an
 * instance another scenario is counting on - which is what has to be
 * said before it happens, naming the scenarios it reaches.
 */
describe('RowActions', () => {
  it('opens the scenario for editing', async () => {
    await setup();

    expect(await item('Edit')).toHaveAttribute('href', '/scenarios/web');
  });

  it('offers a start while something in it is not running', async () => {
    await setup({ hasInactive: true });

    expect(await item('Start')).toBeEnabled();
  });

  it('offers no start once everything in it runs', async () => {
    await setup({ hasInactive: false });

    expect(await item('Start')).toBeDisabled();
  });

  it('offers no stop while nothing in it runs', async () => {
    await setup({ hasRunning: false });

    expect(await item('Stop')).toBeDisabled();
  });

  it('offers a stop once something in it runs', async () => {
    await setup({ hasRunning: true });

    expect(await item('Stop')).toBeEnabled();
  });

  it('starts every instance of the scenario at once', async () => {
    const user = await setup({ hasInactive: true });

    await user.click(await item('Start'));

    expect(MUTATIONS.start.mutate).toHaveBeenCalledWith(
      { ids: ['web-live', 'web-batch'] },
      expect.anything()
    );

    // Each row has to say "starting" now rather than after the next
    // poll, so the status of every instance is written ahead.
    expect(MUTATIONS.status.mutate).toHaveBeenCalledTimes(2);
  });

  it('stops every instance of a scenario nothing else shares', async () => {
    const user = await setup({ hasRunning: true, affected: [] });

    await user.click(await item('Stop'));

    expect(MUTATIONS.stop.mutate).toHaveBeenCalledWith(
      { ids: ['web-live', 'web-batch'] },
      expect.anything()
    );
  });

  it('says which other scenarios a stop would reach', async () => {
    const user = await setup({ hasRunning: true, affected: ['nightly'] });

    await user.click(await item('Stop'));

    const dialog = await screen.findByRole('dialog');
    expect(dialog).toHaveTextContent('Shared instances detected');
    expect(dialog).toHaveTextContent('nightly');
    expect(MUTATIONS.stop.mutate).not.toHaveBeenCalled();
  });

  it('stops the shared instances once that is confirmed', async () => {
    const user = await setup({ hasRunning: true, affected: ['nightly'] });

    await user.click(await item('Stop'));
    const dialog = await screen.findByRole('dialog');
    await user.click(
      within(dialog).getByRole('button', { name: 'Stop anyway' })
    );

    expect(MUTATIONS.stop.mutate).toHaveBeenCalled();
  });

  it('names the scenario in the confirmation of a delete', async () => {
    const user = await setup();

    await user.click(await item('Delete'));

    const dialog = await screen.findByRole('dialog');
    expect(dialog).toHaveTextContent('web');
    expect(MUTATIONS.remove.mutate).not.toHaveBeenCalled();
  });

  it('deletes the scenario once the delete is confirmed', async () => {
    const user = await setup();

    await user.click(await item('Delete'));
    const dialog = await screen.findByRole('dialog');
    await user.click(within(dialog).getByRole('button', { name: 'Delete' }));

    expect(MUTATIONS.remove.mutate).toHaveBeenCalledWith(
      'web',
      expect.anything()
    );
  });
});
