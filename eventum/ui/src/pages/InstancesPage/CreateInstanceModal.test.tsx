import { ModalsProvider } from '@mantine/modals';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { CreateInstanceModal } from './CreateInstanceModal';
import {
  useGeneratorConfigPathMutation,
  useGeneratorDirs,
} from '@/api/hooks/useGeneratorConfigs';
import { useAddGeneratorMutation } from '@/api/hooks/useGenerators';
import { useAddGeneratorToStartupMutation } from '@/api/hooks/useStartup';
import { renderWithProviders } from '@/test/render';

vi.mock('@/api/hooks/useGeneratorConfigs');
vi.mock('@/api/hooks/useGenerators');
vi.mock('@/api/hooks/useStartup');

const resolvePath = { mutate: vi.fn(), isPending: false };
const addGenerator = { mutate: vi.fn(), isPending: false };
const addToStartup = { mutate: vi.fn(), isPending: false };

function setup(
  projects: string[] | null = ['web', 'db'],
  existing: string[] = [],
  state: Record<string, unknown> = {}
) {
  vi.mocked(useGeneratorDirs).mockReturnValue({
    data: projects ?? undefined,
    isLoading: false,
    isError: false,
    isSuccess: projects !== null,
    error: null,
    ...state,
  } as unknown as ReturnType<typeof useGeneratorDirs>);

  renderWithProviders(
    <ModalsProvider>
      <CreateInstanceModal existingInstanceIds={existing} />
    </ModalsProvider>
  );
}

beforeEach(() => {
  vi.clearAllMocks();

  for (const mutation of [resolvePath, addGenerator, addToStartup]) {
    mutation.mutate.mockReset();
  }

  // The project is picked by name; its path is resolved on the backend.
  resolvePath.mutate.mockImplementation(
    (_variables: unknown, handlers?: { onSuccess?: (path: string) => void }) =>
      handlers?.onSuccess?.('/generators/web/generator.yml')
  );
  addGenerator.mutate.mockImplementation(
    (_variables: unknown, handlers?: { onSuccess?: () => void }) =>
      handlers?.onSuccess?.()
  );

  vi.mocked(useGeneratorConfigPathMutation).mockReturnValue(
    resolvePath as unknown as ReturnType<typeof useGeneratorConfigPathMutation>
  );
  vi.mocked(useAddGeneratorMutation).mockReturnValue(
    addGenerator as unknown as ReturnType<typeof useAddGeneratorMutation>
  );
  vi.mocked(useAddGeneratorToStartupMutation).mockReturnValue(
    addToStartup as unknown as ReturnType<
      typeof useAddGeneratorToStartupMutation
    >
  );
});

/**
 * The dropdown of a Mantine select renders in a portal that jsdom does
 * not lay out, so its options are read from the listbox directly.
 */
function option(name: string): HTMLElement {
  const found = [
    ...document.querySelectorAll('[role="listbox"] [role="option"]'),
  ].find((element) => element.textContent === name);

  if (found === undefined) {
    throw new Error(`no option named ${name} is offered`);
  }

  return found as HTMLElement;
}

/**
 * An instance is a project under a name, and the path it runs is
 * resolved on the backend rather than typed here. A registered instance
 * also has to reach the startup file, or it disappears on the next
 * restart.
 */
describe('CreateInstanceModal', () => {
  it('offers the projects of the workspace to pick from', async () => {
    const user = userEvent.setup();
    setup();

    await user.click(screen.getByRole('textbox', { name: /Project name/ }));

    expect(option('web')).toBeInTheDocument();
    expect(option('db')).toBeInTheDocument();
  });

  it('offers no creation until both a name and a project are given', () => {
    setup();

    expect(screen.getByRole('button', { name: 'Create' })).toBeDisabled();
  });

  it('refuses a name another instance already has', async () => {
    const user = userEvent.setup();
    setup(['web'], ['web-prod']);

    await user.type(
      screen.getByRole('textbox', { name: /Instance name/ }),
      'web-prod'
    );

    expect(
      await screen.findByText('Instance with this name already exists')
    ).toBeVisible();
  });

  it('registers the instance under the resolved project path', async () => {
    const user = userEvent.setup();
    setup();

    await user.type(
      screen.getByRole('textbox', { name: /Instance name/ }),
      'web-prod'
    );
    await user.click(screen.getByRole('textbox', { name: /Project name/ }));
    await user.click(option('web'));
    await user.click(screen.getByRole('button', { name: 'Create' }));

    expect(resolvePath.mutate.mock.calls[0]?.[0]).toEqual({ name: 'web' });

    const sent = addGenerator.mutate.mock.calls[0]?.[0] as {
      id: string;
      params: { path: string };
    };

    expect(sent.id).toBe('web-prod');
    expect(sent.params.path).toBe('/generators/web/generator.yml');
  });

  it('writes the instance into the startup file, not starting it', async () => {
    const user = userEvent.setup();
    setup();

    await user.type(
      screen.getByRole('textbox', { name: /Instance name/ }),
      'web-prod'
    );
    await user.click(screen.getByRole('textbox', { name: /Project name/ }));
    await user.click(option('web'));
    await user.click(screen.getByRole('button', { name: 'Create' }));

    const sent = addToStartup.mutate.mock.calls[0]?.[0] as {
      params: { autostart: boolean; scenarios: string[] };
    };

    expect(sent.params.autostart).toBe(false);
    expect(sent.params.scenarios).toEqual([]);
  });

  it('points at the projects page when there are none', () => {
    setup([]);

    expect(screen.getByText(/Have no projects/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Create new' })).toHaveAttribute(
      'href',
      '/projects'
    );
  });

  it('waits while the projects are being read', () => {
    setup(null, [], { isLoading: true, isSuccess: false });

    expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
  });

  it('reports a failure to read them', () => {
    setup(null, [], {
      isLoading: false,
      isSuccess: false,
      isError: true,
      error: new Error('no connection'),
    });

    expect(
      screen.getByText('Failed to load list of projects')
    ).toBeInTheDocument();
  });
});
