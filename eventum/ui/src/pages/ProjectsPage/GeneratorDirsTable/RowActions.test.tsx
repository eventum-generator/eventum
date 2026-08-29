import { ActionIcon } from '@mantine/core';
import { ModalsProvider } from '@mantine/modals';
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { RowActions } from './RowActions';
import * as configs from '@/api/hooks/useGeneratorConfigs';
import { renderWithProviders } from '@/test/render';

vi.mock('@/api/hooks/useGeneratorConfigs');

const remove = { mutate: vi.fn(), isPending: false };

async function setup(generatorIds: string[] = []) {
  vi.mocked(configs.useDeleteGeneratorConfigMutation).mockReturnValue(
    remove as never
  );
  vi.mocked(configs.useGeneratorDirs).mockReturnValue({
    data: [{ name: 'web' }, { name: 'api' }],
  } as never);
  vi.mocked(configs.useRenameGeneratorConfigMutation).mockReturnValue({
    mutate: vi.fn(),
    isPending: false,
  } as never);

  const user = userEvent.setup();

  renderWithProviders(
    <MemoryRouter>
      <ModalsProvider>
        <RowActions
          target={<ActionIcon aria-label="Project actions" />}
          dirName="web"
          generatorIds={generatorIds}
        />
      </ModalsProvider>
    </MemoryRouter>
  );

  await user.click(screen.getByRole('button', { name: 'Project actions' }));

  return user;
}

async function item(name: string): Promise<HTMLElement> {
  return await screen.findByRole('menuitem', { name });
}

beforeEach(() => {
  vi.clearAllMocks();
});

/**
 * A project is a directory, and an instance points at it by path. So
 * deleting one that an instance still runs would leave that instance
 * pointing at nothing - the menu has to stop it and say which instances
 * stand in the way, rather than fail on the request.
 */
describe('RowActions', () => {
  it('opens the project for editing', async () => {
    await setup();

    expect(await item('Edit')).toHaveAttribute('href', '/projects/web');
  });

  it('names the project in the confirmation of a delete', async () => {
    const user = await setup([]);

    await user.click(await item('Delete'));

    const dialog = await screen.findByRole('dialog');
    expect(dialog).toHaveTextContent('Project web will be deleted');
  });

  it('deletes the project once the delete is confirmed', async () => {
    const user = await setup([]);

    await user.click(await item('Delete'));
    const dialog = await screen.findByRole('dialog');
    await user.click(within(dialog).getByRole('button', { name: 'Delete' }));

    expect(remove.mutate).toHaveBeenCalledWith(
      { name: 'web' },
      expect.anything()
    );
  });

  it('keeps the project when the confirmation is dismissed', async () => {
    const user = await setup([]);

    await user.click(await item('Delete'));
    const dialog = await screen.findByRole('dialog');
    await user.click(within(dialog).getByRole('button', { name: 'Cancel' }));

    expect(remove.mutate).not.toHaveBeenCalled();
  });

  it('refuses to delete a project an instance runs, and names them', async () => {
    const user = await setup(['web-live', 'web-batch']);

    await user.click(await item('Delete'));

    const dialog = await screen.findByRole('dialog');
    expect(dialog).toHaveTextContent('Unable to delete');
    expect(dialog).toHaveTextContent('web-live');
    expect(dialog).toHaveTextContent('web-batch');

    // No confirmation is offered at all, so there is nothing to press
    // through by habit.
    expect(within(dialog).queryByRole('button', { name: 'Delete' })).toBeNull();
    expect(remove.mutate).not.toHaveBeenCalled();
  });

  it('tells the rename which instances follow the project', async () => {
    const user = await setup(['web-live']);

    await user.click(await item('Rename'));

    const dialog = await screen.findByRole('dialog');
    expect(dialog).toHaveTextContent('web-live');
    expect(dialog).toHaveTextContent('All of them must be stopped');
  });

  it('offers a rename of a project nothing points at', async () => {
    const user = await setup([]);

    await user.click(await item('Rename'));

    const dialog = await screen.findByRole('dialog');
    expect(dialog).toHaveTextContent('No instance uses this project.');
  });
});
