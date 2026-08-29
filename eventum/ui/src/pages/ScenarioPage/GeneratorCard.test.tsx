import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { GeneratorCard, GeneratorCardProps } from './GeneratorCard';
import * as generators from '@/api/hooks/useGenerators';
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

const start = { mutate: vi.fn(), isPending: false };
const stop = { mutate: vi.fn(), isPending: false };

function setup(overrides: Partial<GeneratorCardProps> = {}) {
  vi.mocked(generators.useStartGeneratorMutation).mockReturnValue(
    start as never
  );
  vi.mocked(generators.useStopGeneratorMutation).mockReturnValue(stop as never);
  vi.mocked(generators.useUpdateGeneratorStatus).mockReturnValue({
    mutate: vi.fn(),
  } as never);

  const onRemove = vi.fn();

  renderWithProviders(
    <MemoryRouter>
      <GeneratorCard
        generatorId="web"
        generatorPath="web/generator.yml"
        status={overrides.status ?? IDLE}
        onRemove={onRemove}
        {...overrides}
      />
    </MemoryRouter>
  );

  return { onRemove, user: userEvent.setup() };
}

async function openMenu(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole('button', { name: 'Instance actions' }));
}

beforeEach(() => {
  vi.clearAllMocks();
});

/**
 * A card is one member of a scenario: what it is, what it is doing, and
 * the actions that apply to it. Starting an instance that already runs
 * or stopping one that does not are both requests the backend refuses,
 * so the menu offers each only in the state it makes sense in.
 */
describe('GeneratorCard', () => {
  it('names the instance and the project it runs', () => {
    setup();

    // The instance and the project it runs carry the same name here.
    expect(screen.getAllByText('web')).toHaveLength(2);
  });

  it('names the path of a configuration outside the workspace', () => {
    setup({ generatorPath: '/opt/eventum/legacy/generator.yml' });

    // There is no project page for it, so the path is what identifies it.
    expect(
      screen.getByText('/opt/eventum/legacy/generator.yml')
    ).toBeInTheDocument();
  });

  it('offers a start, and no stop, for an instance at rest', async () => {
    const { user } = setup({ status: IDLE });

    await openMenu(user);

    // Only the action that applies is drawn at all, so there is nothing
    // to press that the backend would refuse.
    expect(
      await screen.findByRole('menuitem', { name: 'Start' })
    ).toBeVisible();
    expect(screen.queryByRole('menuitem', { name: 'Stop' })).toBeNull();
  });

  it('offers a stop, and no start, for one that runs', async () => {
    const { user } = setup({ status: RUNNING });

    await openMenu(user);

    expect(await screen.findByRole('menuitem', { name: 'Stop' })).toBeVisible();
    expect(screen.queryByRole('menuitem', { name: 'Start' })).toBeNull();
  });

  it('starts the instance', async () => {
    const { user } = setup({ status: IDLE });

    await openMenu(user);
    await user.click(await screen.findByRole('menuitem', { name: 'Start' }));

    expect(start.mutate).toHaveBeenCalledWith({ id: 'web' }, expect.anything());
  });

  it('stops the instance', async () => {
    const { user } = setup({ status: RUNNING });

    await openMenu(user);
    await user.click(await screen.findByRole('menuitem', { name: 'Stop' }));

    expect(stop.mutate).toHaveBeenCalledWith({ id: 'web' }, expect.anything());
  });

  it('leads to the instance and to the project it runs', async () => {
    const { user } = setup();

    await openMenu(user);

    expect(
      await screen.findByRole('menuitem', { name: 'Edit instance' })
    ).toHaveAttribute('href', '/instances/web');
    expect(
      await screen.findByRole('menuitem', { name: 'Go to project' })
    ).toHaveAttribute('href', '/projects/web');
  });

  it('offers no project page for a configuration outside the workspace', async () => {
    const { user } = setup({
      generatorPath: '/opt/eventum/legacy/generator.yml',
    });

    await openMenu(user);

    expect(
      screen.queryByRole('menuitem', { name: 'Go to project' })
    ).toBeNull();
  });

  it('takes the instance out of the scenario', async () => {
    const { user, onRemove } = setup();

    await openMenu(user);
    await user.click(await screen.findByRole('menuitem', { name: 'Remove' }));

    expect(onRemove).toHaveBeenCalledTimes(1);
  });

  it('draws no state of its own before the live status arrives', () => {
    setup({ status: undefined });

    // The pill is always drawn, reading as inactive until the real
    // status is known - a card with no pill would read as broken.
    expect(screen.getByText(/Idle|Inactive/)).toBeInTheDocument();
  });

  it('lists what the instance shares once it is expanded', () => {
    setup({
      isExpanded: true,
      globalsUsage: {
        writes: [{ key: 'session', path: 'templates/main.jinja' }],
        reads: [],
      } as never,
    });

    expect(screen.getByText('writes')).toBeInTheDocument();
    expect(screen.getByText('session')).toBeInTheDocument();
  });
});
