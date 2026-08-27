import { ModalsProvider } from '@mantine/modals';
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { InstanceHeader } from './InstanceHeader';
import * as generatorHooks from '@/api/hooks/useGenerators';
import { GeneratorStatus } from '@/api/routes/generators/schemas';
import { renderWithProviders } from '@/test/render';

vi.mock('@/api/hooks/useGenerators');

const IDLE: GeneratorStatus = {
  is_initializing: false,
  is_running: false,
  is_ended_up: false,
  is_ended_up_successfully: false,
  is_stopping: false,
};

const RUNNING: GeneratorStatus = { ...IDLE, is_running: true };
const STARTING: GeneratorStatus = { ...IDLE, is_initializing: true };

const start = { mutate: vi.fn(), isPending: false };
const stop = { mutate: vi.fn(), isPending: false };

interface Options {
  status?: GeneratorStatus;
  isDirty?: boolean;
  startTime?: string | null;
}

function setup(options: Options = {}) {
  const status = options.status ?? IDLE;

  vi.mocked(generatorHooks.useStartGeneratorMutation).mockReturnValue(
    start as never
  );
  vi.mocked(generatorHooks.useStopGeneratorMutation).mockReturnValue(
    stop as never
  );
  vi.mocked(generatorHooks.useUpdateGeneratorStatus).mockReturnValue({
    mutate: vi.fn(),
  } as never);
  vi.mocked(generatorHooks.useGenerators).mockReturnValue({
    data: [
      {
        id: 'web',
        path: 'web/generator.yml',
        status,
        start_time: options.startTime ?? null,
      },
    ],
  } as never);

  const onSave = vi.fn();
  const onBack = vi.fn();

  renderWithProviders(
    <MemoryRouter>
      <ModalsProvider>
        <InstanceHeader
          instanceId="web"
          status={status}
          isDirty={options.isDirty ?? false}
          isSaving={false}
          onSave={onSave}
          onBack={onBack}
        />
      </ModalsProvider>
    </MemoryRouter>
  );

  return { onSave, onBack, user: userEvent.setup() };
}

beforeEach(() => {
  vi.clearAllMocks();
});

/**
 * The header is where an instance is started, stopped and saved, so what
 * it offers has to follow the state of the instance: a save appears only
 * with something to save, and a restart only for an instance that is
 * actually running - restarting one that is not would stop nothing and
 * start it twice.
 */
describe('InstanceHeader', () => {
  it('names the instance', () => {
    setup();

    expect(screen.getByRole('heading', { name: 'web' })).toBeVisible();
  });

  it('offers a start for an instance at rest', () => {
    setup({ status: IDLE });

    expect(screen.getByRole('button', { name: /Start/ })).toBeVisible();
    expect(screen.queryByRole('button', { name: /^Stop/ })).toBeNull();
  });

  it('offers a stop and a restart for one that runs', () => {
    setup({ status: RUNNING });

    expect(screen.getByRole('button', { name: /Stop/ })).toBeEnabled();
    expect(screen.getByRole('button', { name: /Restart/ })).toBeVisible();
  });

  it('offers no restart while it is still starting', () => {
    setup({ status: STARTING });

    // There is nothing to restart yet, and the stop has to wait for the
    // run to exist.
    expect(screen.queryByRole('button', { name: /Restart/ })).toBeNull();
    expect(screen.getByRole('button', { name: /Stop/ })).toBeDisabled();
  });

  it('starts the instance', async () => {
    const { user } = setup({ status: IDLE });

    await user.click(screen.getByRole('button', { name: /Start/ }));

    expect(start.mutate).toHaveBeenCalled();
  });

  it('stops the instance', async () => {
    const { user } = setup({ status: RUNNING });

    await user.click(screen.getByRole('button', { name: /Stop/ }));

    expect(stop.mutate).toHaveBeenCalled();
  });

  it('asks before restarting, and does nothing when refused', async () => {
    const { user } = setup({ status: RUNNING });

    await user.click(screen.getByRole('button', { name: /Restart/ }));

    const dialog = await screen.findByRole('dialog');
    expect(dialog).toHaveTextContent('Restart instance');

    await user.click(within(dialog).getByRole('button', { name: 'Cancel' }));

    expect(stop.mutate).not.toHaveBeenCalled();
  });

  it('offers no save with nothing to save', () => {
    setup({ isDirty: false });

    expect(screen.queryByRole('button', { name: 'Save' })).toBeNull();
  });

  it('saves the edited settings', async () => {
    const { user, onSave } = setup({ isDirty: true });

    await user.click(screen.getByRole('button', { name: 'Save' }));

    expect(onSave).toHaveBeenCalledTimes(1);
  });

  it('says how long a running instance has been up', () => {
    setup({
      status: RUNNING,
      startTime: new Date(Date.now() - 60_000).toISOString(),
    });

    expect(screen.getByText(/up/)).toBeInTheDocument();
  });

  it('says nothing about uptime for an instance at rest', () => {
    setup({ status: IDLE, startTime: '2026-01-01T00:00:00+00:00' });

    expect(screen.queryByText(/^up/)).toBeNull();
  });

  it('leads back to the instances', async () => {
    const { user, onBack } = setup();

    await user.click(screen.getByRole('button', { name: 'Back to instances' }));

    expect(onBack).toHaveBeenCalledTimes(1);
  });
});
