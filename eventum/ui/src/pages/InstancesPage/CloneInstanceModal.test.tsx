import { ModalsProvider } from '@mantine/modals';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { CloneInstanceModal } from './CloneInstanceModal';
import {
  useAddGeneratorMutation,
  useGenerator,
} from '@/api/hooks/useGenerators';
import {
  useAddGeneratorToStartupMutation,
  useStartupGenerator,
} from '@/api/hooks/useStartup';
import { renderWithProviders } from '@/test/render';

vi.mock('@/api/hooks/useGenerators');
vi.mock('@/api/hooks/useStartup');

const PARAMS = {
  id: 'web',
  path: '/generators/web/generator.yml',
  timezone: 'UTC',
};

const STARTUP_PARAMS = {
  ...PARAMS,
  autostart: true,
  scenarios: ['corp'],
};

const addGenerator = { mutate: vi.fn(), isPending: false };
const addToStartup = { mutate: vi.fn(), isPending: false };

function query(data: unknown, state: Record<string, unknown> = {}) {
  return {
    data,
    isLoading: false,
    isError: false,
    isSuccess: data !== undefined,
    error: null,
    ...state,
  };
}

function setup(
  existing: string[] = [],
  states: {
    generator?: Record<string, unknown>;
    startup?: Record<string, unknown>;
  } = {}
) {
  vi.mocked(useGenerator).mockReturnValue(
    query(
      states.generator ? undefined : PARAMS,
      states.generator
    ) as unknown as ReturnType<typeof useGenerator>
  );
  vi.mocked(useStartupGenerator).mockReturnValue(
    query(
      states.startup ? undefined : STARTUP_PARAMS,
      states.startup
    ) as unknown as ReturnType<typeof useStartupGenerator>
  );

  renderWithProviders(
    <ModalsProvider>
      <CloneInstanceModal
        sourceInstanceId="web"
        existingInstanceIds={existing}
      />
    </ModalsProvider>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  addGenerator.mutate.mockReset();
  addToStartup.mutate.mockReset();
  addGenerator.mutate.mockImplementation(
    (_variables: unknown, handlers?: { onSuccess?: () => void }) =>
      handlers?.onSuccess?.()
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
 * A clone is the source instance under another name, so everything but
 * the name has to be carried over - including the startup-only fields,
 * which live in a different record and would otherwise be silently
 * dropped.
 */
describe('CloneInstanceModal', () => {
  it('names the instance being cloned', () => {
    setup();

    expect(screen.getByText(/Cloning/)).toHaveTextContent('web');
  });

  it('proposes a name based on the source', () => {
    setup();

    expect(
      screen.getByRole('textbox', { name: /New instance name/ })
    ).not.toHaveValue('');
  });

  it('offers no clone once the name is cleared', async () => {
    const user = userEvent.setup();
    setup();

    await user.clear(
      screen.getByRole('textbox', { name: /New instance name/ })
    );

    expect(screen.getByRole('button', { name: 'Clone' })).toBeDisabled();
  });

  it('refuses a name another instance already has', async () => {
    const user = userEvent.setup();
    setup(['web-2']);

    const name = screen.getByRole('textbox', { name: /New instance name/ });
    await user.clear(name);
    await user.type(name, 'web-2');

    expect(
      await screen.findByText('Instance with this name already exists')
    ).toBeVisible();
    expect(screen.getByRole('button', { name: 'Clone' })).toBeDisabled();
  });

  it('registers the clone under the new name', async () => {
    const user = userEvent.setup();
    setup();

    const name = screen.getByRole('textbox', { name: /New instance name/ });
    await user.clear(name);
    await user.type(name, 'web-2');
    await user.click(screen.getByRole('button', { name: 'Clone' }));

    const sent = addGenerator.mutate.mock.calls[0]?.[0] as {
      id: string;
      params: { path: string };
    };

    expect(sent.id).toBe('web-2');
    expect(sent.params.path).toBe(PARAMS.path);
  });

  it('carries the startup-only settings of the source over', async () => {
    const user = userEvent.setup();
    setup();

    const name = screen.getByRole('textbox', { name: /New instance name/ });
    await user.clear(name);
    await user.type(name, 'web-2');
    await user.click(screen.getByRole('button', { name: 'Clone' }));

    const sent = addToStartup.mutate.mock.calls[0]?.[0] as {
      id: string;
      params: { autostart: boolean; scenarios: string[] };
    };

    expect(sent.id).toBe('web-2');
    expect(sent.params.autostart).toBe(true);
    expect(sent.params.scenarios).toEqual(['corp']);
  });

  it('waits while either record is being read', () => {
    setup([], { generator: { isLoading: true, isSuccess: false } });

    expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
  });

  it('reports a failure to read the instance parameters', () => {
    setup([], {
      generator: {
        isLoading: false,
        isSuccess: false,
        isError: true,
        error: new Error('no connection'),
      },
    });

    expect(
      screen.getByText('Failed to get instance parameters')
    ).toBeInTheDocument();
  });

  it('reports a failure to read the startup definition', () => {
    setup([], {
      startup: {
        isLoading: false,
        isSuccess: false,
        isError: true,
        error: new Error('no connection'),
      },
    });

    expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
    expect(screen.getByText(/no connection/)).toBeInTheDocument();
  });
});
