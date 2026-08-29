import { ModalsProvider } from '@mantine/modals';
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { DangerZone } from './DangerZone';
import {
  useRestartInstanceMutation,
  useStopInstanceMutation,
} from '@/api/hooks/useInstance';
import { renderWithProviders } from '@/test/render';

vi.mock('@/api/hooks/useInstance');

interface Mutation {
  mutate: ReturnType<typeof vi.fn>;
  isPending: boolean;
}

let restart: Mutation;
let stop: Mutation;

function mutation(succeeds = true): Mutation {
  return {
    mutate: vi.fn(
      (
        _variables: unknown,
        handlers?: {
          onSuccess?: () => void;
          onError?: (error: Error) => void;
        }
      ) => {
        if (succeeds) {
          handlers?.onSuccess?.();
        } else {
          handlers?.onError?.(new Error('no connection'));
        }
      }
    ),
    isPending: false,
  };
}

function setup(overrides: { restart?: Mutation; stop?: Mutation } = {}) {
  restart = overrides.restart ?? mutation();
  stop = overrides.stop ?? mutation();

  vi.mocked(useRestartInstanceMutation).mockReturnValue(
    restart as unknown as ReturnType<typeof useRestartInstanceMutation>
  );
  vi.mocked(useStopInstanceMutation).mockReturnValue(
    stop as unknown as ReturnType<typeof useStopInstanceMutation>
  );

  const onTransition = vi.fn();

  renderWithProviders(
    <ModalsProvider>
      <DangerZone onTransition={onTransition} />
    </ModalsProvider>
  );

  return onTransition;
}

beforeEach(() => {
  vi.clearAllMocks();
});

/**
 * Both actions here take the instance down, and stopping it cannot be
 * undone from the web interface at all. Neither may therefore happen on
 * a single click, and the page must only claim a transition once the
 * instance has actually accepted the request.
 */
describe('DangerZone', () => {
  it('offers both actions', () => {
    setup();

    expect(screen.getByRole('button', { name: /Restart/ })).toBeEnabled();
    expect(screen.getByRole('button', { name: /Stop/ })).toBeEnabled();
  });

  it('says that stopping cannot be undone from here', () => {
    setup();

    expect(
      screen.getByText(/not be able to start it again from the web interface/)
    ).toBeInTheDocument();
  });

  it('confirms before restarting', async () => {
    const user = userEvent.setup();
    const onTransition = setup();

    await user.click(screen.getByRole('button', { name: /Restart/ }));

    const dialog = await screen.findByRole('dialog');
    expect(restart.mutate).not.toHaveBeenCalled();

    await user.click(within(dialog).getByRole('button', { name: 'Restart' }));

    expect(restart.mutate).toHaveBeenCalledTimes(1);
    expect(onTransition).toHaveBeenCalledWith('restarting');
  });

  it('confirms before stopping', async () => {
    const user = userEvent.setup();
    const onTransition = setup();

    await user.click(screen.getByRole('button', { name: /Stop/ }));

    const dialog = await screen.findByRole('dialog');
    expect(stop.mutate).not.toHaveBeenCalled();

    await user.click(within(dialog).getByRole('button', { name: 'Stop' }));

    expect(stop.mutate).toHaveBeenCalledTimes(1);
    expect(onTransition).toHaveBeenCalledWith('stopping');
  });

  it('does nothing when a confirmation is dismissed', async () => {
    const user = userEvent.setup();
    const onTransition = setup();

    await user.click(screen.getByRole('button', { name: /Stop/ }));
    await user.click(
      within(await screen.findByRole('dialog')).getByRole('button', {
        name: 'Cancel',
      })
    );

    expect(stop.mutate).not.toHaveBeenCalled();
    expect(onTransition).not.toHaveBeenCalled();
  });

  it('claims no transition when the request failed', async () => {
    const user = userEvent.setup();
    const onTransition = setup({ restart: mutation(false) });

    await user.click(screen.getByRole('button', { name: /Restart/ }));
    await user.click(
      within(await screen.findByRole('dialog')).getByRole('button', {
        name: 'Restart',
      })
    );

    expect(restart.mutate).toHaveBeenCalledTimes(1);
    expect(onTransition).not.toHaveBeenCalled();
  });

  it('shows the action in flight while the request is out', () => {
    setup({ stop: { ...mutation(), isPending: true } });

    expect(screen.getByRole('button', { name: /Stop/ })).toHaveAttribute(
      'data-loading',
      'true'
    );
  });
});
