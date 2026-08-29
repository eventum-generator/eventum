import { ActionIcon } from '@mantine/core';
import { ModalsProvider } from '@mantine/modals';
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { RowActions } from './RowActions';
import * as generators from '@/api/hooks/useGenerators';
import * as startup from '@/api/hooks/useStartup';
import { GeneratorStatus } from '@/api/routes/generators/schemas';
import { renderWithProviders } from '@/test/render';

vi.mock('@/api/hooks/useGenerators');
vi.mock('@/api/hooks/useStartup');

const IDLE: GeneratorStatus = {
  is_initializing: false,
  is_running: false,
  is_ended_up: false,
  is_ended_up_successfully: false,
  is_stopping: false,
};

const RUNNING: GeneratorStatus = { ...IDLE, is_running: true };
const STARTING: GeneratorStatus = { ...IDLE, is_initializing: true };
const STOPPING: GeneratorStatus = { ...IDLE, is_stopping: true };

const MUTATIONS = {
  start: { mutate: vi.fn(), isPending: false },
  stop: { mutate: vi.fn(), isPending: false },
  remove: { mutate: vi.fn(), isPending: false },
  removeFromStartup: { mutate: vi.fn(), isPending: false },
  status: { mutate: vi.fn(), isPending: false },
};

async function setup(status: GeneratorStatus = IDLE) {
  vi.mocked(generators.useStartGeneratorMutation).mockReturnValue(
    MUTATIONS.start as never
  );
  vi.mocked(generators.useStopGeneratorMutation).mockReturnValue(
    MUTATIONS.stop as never
  );
  vi.mocked(generators.useDeleteGeneratorMutation).mockReturnValue(
    MUTATIONS.remove as never
  );
  vi.mocked(generators.useUpdateGeneratorStatus).mockReturnValue(
    MUTATIONS.status as never
  );
  vi.mocked(startup.useDeleteGeneratorFromStartupMutation).mockReturnValue(
    MUTATIONS.removeFromStartup as never
  );

  const user = userEvent.setup();

  renderWithProviders(
    <MemoryRouter>
      <ModalsProvider>
        <RowActions
          target={<ActionIcon aria-label="Instance actions" />}
          instanceId="web"
          instanceStatus={status}
          existingInstanceIds={['web', 'api']}
        />
      </ModalsProvider>
    </MemoryRouter>
  );

  await user.click(screen.getByRole('button', { name: 'Instance actions' }));

  return user;
}

/**
 * A menu entry. The dropdown is mounted through a transition, so it is
 * awaited rather than read straight after the click that opened it.
 */
async function item(name: string): Promise<HTMLElement> {
  return await screen.findByRole('menuitem', { name });
}

beforeEach(() => {
  vi.clearAllMocks();
});

/**
 * The menu of an instance row offers everything that can be done to it,
 * and what can be done depends on what it is doing. Renaming or deleting
 * an instance that is running would act on a process in flight, and the
 * metrics only exist while it produces - so the state of the instance is
 * what decides, and each state has to be read the same way.
 */
describe('RowActions', () => {
  it('offers everything for an instance at rest', async () => {
    await setup(IDLE);

    expect(await item('Rename')).toBeEnabled();
    expect(await item('Clone')).toBeEnabled();
    expect(await item('Start')).toBeEnabled();
    expect(await item('Delete')).toBeEnabled();
  });

  it.each([
    ['a running instance', RUNNING],
    ['one still starting', STARTING],
    ['one still stopping', STOPPING],
  ])('holds back what must not act on %s', async (_label, status) => {
    await setup(status);

    expect(await item('Rename')).toBeDisabled();
    expect(await item('Start')).toBeDisabled();
    expect(await item('Delete')).toBeDisabled();
  });

  it('offers a stop only while there is something to stop', async () => {
    await setup(RUNNING);

    expect(await item('Stop')).toBeEnabled();
  });

  it.each([
    ['at rest', IDLE],
    ['still starting', STARTING],
  ])('offers no stop for an instance %s', async (_label, status) => {
    await setup(status);

    expect(await item('Stop')).toBeDisabled();
  });

  it('offers the metrics of a running instance', async () => {
    await setup(RUNNING);

    expect(await item('Show metrics')).toBeEnabled();
  });

  it('offers no metrics for an instance at rest', async () => {
    await setup(IDLE);

    // Stats are served for a live pipeline, so there is nothing to open.
    expect(await item('Show metrics')).toBeDisabled();
  });

  it('offers the log of an instance whatever it is doing', async () => {
    await setup(IDLE);

    // A log outlives the run that wrote it, which is when it is read.
    expect(await item('Show logs')).toBeEnabled();
  });

  it('opens the instance for editing', async () => {
    await setup();

    expect(await item('Edit')).toHaveAttribute('href', '/instances/web');
  });

  it('marks the instance as starting before the request answers', async () => {
    const user = await setup(IDLE);

    await user.click(await item('Start'));

    // The table reads its rows from the cache, so the row has to say
    // "starting" now rather than after the next poll.
    expect(MUTATIONS.status.mutate).toHaveBeenCalledWith({
      id: 'web',
      status: expect.objectContaining({
        is_initializing: true,
        is_running: false,
      }),
    });
    expect(MUTATIONS.start.mutate).toHaveBeenCalledWith(
      { id: 'web' },
      expect.anything()
    );
  });

  it('marks the instance as stopping before the request answers', async () => {
    const user = await setup(RUNNING);

    await user.click(await item('Stop'));

    expect(MUTATIONS.status.mutate).toHaveBeenCalledWith({
      id: 'web',
      status: expect.objectContaining({ is_stopping: true }),
    });
    expect(MUTATIONS.stop.mutate).toHaveBeenCalledWith(
      { id: 'web' },
      expect.anything()
    );
  });

  it('names the instance in the confirmation of a delete', async () => {
    const user = await setup(IDLE);

    await user.click(await item('Delete'));

    const dialog = await screen.findByRole('dialog');
    expect(dialog).toHaveTextContent('Instance web will be deleted');
    expect(MUTATIONS.remove.mutate).not.toHaveBeenCalled();
  });

  it('deletes the instance once the delete is confirmed', async () => {
    const user = await setup(IDLE);

    await user.click(await item('Delete'));
    const dialog = await screen.findByRole('dialog');
    await user.click(within(dialog).getByRole('button', { name: 'Delete' }));

    expect(MUTATIONS.remove.mutate).toHaveBeenCalledWith(
      { id: 'web' },
      expect.anything()
    );
  });

  it('does not delete the instance when the confirmation is dismissed', async () => {
    const user = await setup(IDLE);

    await user.click(await item('Delete'));
    const dialog = await screen.findByRole('dialog');
    await user.click(within(dialog).getByRole('button', { name: 'Cancel' }));

    expect(MUTATIONS.remove.mutate).not.toHaveBeenCalled();
  });

  it('offers a clone of the instance', async () => {
    // What the clone modal then asks for is covered where it can be
    // reached with the data it reads - in the browser suite.
    await setup(IDLE);

    expect(await item('Clone')).toBeEnabled();
  });
});
