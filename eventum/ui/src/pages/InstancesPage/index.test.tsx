import { ModalsProvider } from '@mantine/modals';
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import InstancesPage from './index';
import * as generatorHooks from '@/api/hooks/useGenerators';
import * as startupHooks from '@/api/hooks/useStartup';
import { GeneratorsInfo } from '@/api/routes/generators/schemas';
import { renderWithProviders } from '@/test/render';

vi.mock('@/api/hooks/useGenerators');
vi.mock('@/api/hooks/useStartup');

const IDLE = {
  is_initializing: false,
  is_running: false,
  is_ended_up: false,
  is_ended_up_successfully: false,
  is_stopping: false,
};

const INSTANCES: GeneratorsInfo = [
  {
    id: 'web',
    path: '/generators/web/generator.yml',
    status: { ...IDLE, is_running: true },
    start_time: '2026-08-20T10:00:00Z',
  },
  {
    id: 'db',
    path: '/generators/db/generator.yml',
    status: IDLE,
    start_time: null,
  },
];

const mutation = () => ({ mutate: vi.fn(), isPending: false });

let bulkStart: ReturnType<typeof mutation>;
let bulkStop: ReturnType<typeof mutation>;
let bulkDelete: ReturnType<typeof mutation>;
let updateStatus: ReturnType<typeof mutation>;

function setup(instances: GeneratorsInfo | null = INSTANCES, state = {}) {
  vi.mocked(generatorHooks.useGenerators).mockReturnValue({
    data: instances ?? undefined,
    isLoading: false,
    isError: false,
    error: null,
    isSuccess: instances !== null,
    refetch: vi.fn(),
    ...state,
  } as unknown as ReturnType<typeof generatorHooks.useGenerators>);

  renderWithProviders(
    <MemoryRouter>
      <ModalsProvider>
        <InstancesPage />
      </ModalsProvider>
    </MemoryRouter>
  );
}

function row(id: string) {
  return screen.getByRole('row', { name: new RegExp(id) });
}

beforeEach(() => {
  vi.clearAllMocks();

  bulkStart = mutation();
  bulkStop = mutation();
  bulkDelete = mutation();
  updateStatus = mutation();

  const generic = {
    useRunningGeneratorsStats: { data: [], refetch: vi.fn() },
    useUpdateGeneratorStatus: updateStatus,
    useBulkStartGeneratorMutation: bulkStart,
    useBulkStopGeneratorMutation: bulkStop,
    useBulkDeleteGeneratorMutation: bulkDelete,
    useStartGeneratorMutation: mutation(),
    useStopGeneratorMutation: mutation(),
    useDeleteGeneratorMutation: mutation(),
  };

  for (const [name, value] of Object.entries(generic)) {
    const hook = generatorHooks[name as keyof typeof generatorHooks];
    vi.mocked(hook as () => unknown).mockReturnValue(value);
  }

  vi.mocked(
    startupHooks.useBulkDeleteGeneratorsFromStartupMutation
  ).mockReturnValue(
    mutation() as unknown as ReturnType<
      typeof startupHooks.useBulkDeleteGeneratorsFromStartupMutation
    >
  );
  vi.mocked(startupHooks.useDeleteGeneratorFromStartupMutation).mockReturnValue(
    mutation() as unknown as ReturnType<
      typeof startupHooks.useDeleteGeneratorFromStartupMutation
    >
  );
});

/**
 * The instances table is the screen an operator watches while
 * generators run, and every action on it is taken against a selection.
 * That makes the selection load-bearing: an action offered with nothing
 * selected, or taken against the wrong rows, acts on instances the user
 * did not name.
 */
describe('InstancesPage', () => {
  it('lists the registered instances', () => {
    setup();

    expect(row('web')).toBeInTheDocument();
    expect(row('db')).toBeInTheDocument();
  });

  it('counts them, and how many are active', () => {
    setup();

    expect(screen.getByText(/2 instances/)).toBeInTheDocument();
    expect(screen.getByText(/1 active/)).toBeInTheDocument();
  });

  it('names the status of each instance', () => {
    setup();

    expect(within(row('web')).getByText('Active')).toBeInTheDocument();
    expect(within(row('db')).getByText('Idle')).toBeInTheDocument();
  });

  it('links each instance to its own page and to its project', () => {
    setup();

    const links = within(row('web')).getAllByRole('link');
    const targets = links.map((link) => link.getAttribute('href'));

    expect(targets).toContain('/instances/web');
    expect(targets.some((href) => href?.includes('/projects/'))).toBe(true);
  });

  it('offers to create the first one when there are none', () => {
    setup([]);

    expect(screen.getByText('No instances yet')).toBeInTheDocument();
  });

  it('waits while the list is being read', () => {
    setup(null, { isLoading: true, isSuccess: false });

    expect(screen.queryByRole('table')).not.toBeInTheDocument();
  });

  it('reports a failure to read it', () => {
    setup(null, {
      isLoading: false,
      isSuccess: false,
      isError: true,
      error: new Error('no connection'),
    });

    expect(
      screen.getByText('Failed to load instances list')
    ).toBeInTheDocument();
  });

  it('offers no bulk action until something is selected', () => {
    setup();

    for (const name of ['Start selected', 'Stop selected', 'Delete selected']) {
      expect(screen.getByRole('button', { name })).toBeDisabled();
    }
  });

  it('offers them once a row is selected', async () => {
    const user = userEvent.setup();
    setup();

    await user.click(within(row('db')).getByRole('checkbox'));

    expect(
      screen.getByRole('button', { name: 'Start selected' })
    ).toBeEnabled();
    expect(screen.getByText('1 selected')).toBeInTheDocument();
  });

  it('starts only the instances that are not running', async () => {
    const user = userEvent.setup();
    setup();

    await user.click(screen.getByRole('checkbox', { name: 'Select all' }));
    await user.click(screen.getByRole('button', { name: 'Start selected' }));

    expect(bulkStart.mutate).toHaveBeenCalledTimes(1);
    // The running instance is marked as starting by nothing; only the
    // idle one transitions.
    expect(updateStatus.mutate).toHaveBeenCalledTimes(1);
    expect(updateStatus.mutate.mock.calls[0]?.[0]).toMatchObject({ id: 'db' });
  });

  it('stops only the instances that are running', async () => {
    const user = userEvent.setup();
    setup();

    await user.click(screen.getByRole('checkbox', { name: 'Select all' }));
    await user.click(screen.getByRole('button', { name: 'Stop selected' }));

    expect(bulkStop.mutate).toHaveBeenCalledTimes(1);
    expect(updateStatus.mutate.mock.calls[0]?.[0]).toMatchObject({ id: 'web' });
  });

  it('confirms before deleting a selection', async () => {
    const user = userEvent.setup();
    setup();

    await user.click(within(row('db')).getByRole('checkbox'));
    await user.click(screen.getByRole('button', { name: 'Delete selected' }));

    const dialog = await screen.findByRole('dialog');
    expect(dialog).toHaveTextContent('db');

    await user.click(within(dialog).getByRole('button', { name: 'Delete' }));

    expect(bulkDelete.mutate).toHaveBeenCalledWith(
      { ids: ['db'] },
      expect.anything()
    );
  });

  it('deletes nothing when the confirmation is dismissed', async () => {
    const user = userEvent.setup();
    setup();

    await user.click(within(row('db')).getByRole('checkbox'));
    await user.click(screen.getByRole('button', { name: 'Delete selected' }));
    await user.click(
      within(await screen.findByRole('dialog')).getByRole('button', {
        name: 'Cancel',
      })
    );

    expect(bulkDelete.mutate).not.toHaveBeenCalled();
  });

  it('filters the list by instance name', async () => {
    const user = userEvent.setup();
    setup();

    await user.type(
      screen.getByPlaceholderText('search by instance...'),
      'web'
    );

    expect(screen.getByRole('row', { name: /web/ })).toBeInTheDocument();
    expect(screen.queryByRole('row', { name: /db/ })).not.toBeInTheDocument();
  });

  it('filters the list down to the active instances', async () => {
    const user = userEvent.setup();
    setup();

    await user.click(screen.getByRole('radio', { name: 'Active' }));

    expect(screen.getByRole('row', { name: /web/ })).toBeInTheDocument();
    expect(screen.queryByRole('row', { name: /db/ })).not.toBeInTheDocument();
  });
});
