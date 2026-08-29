import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import TimestampsHistogram from './index';
import { useGenerateTimestampsMutation } from '@/api/hooks/usePreview';
import { InputPluginsNamedConfig } from '@/api/routes/generator-configs/schemas';
import { ProjectNameProvider } from '@/pages/ProjectPage/context/ProjectNameContext';
import { renderWithProviders } from '@/test/render';

vi.mock('@/api/hooks/usePreview');

const CONFIGS: InputPluginsNamedConfig = [
  { timer: { seconds: 5, count: 1 } },
  { cron: { expression: '* * * * *', count: 2 } },
] as unknown as InputPluginsNamedConfig;

const RESULT = {
  span_edges: ['2026-08-20T10:00:00', '2026-08-20T10:00:05'],
  span_counts: { timer: [2, 3] },
  total: 5,
  first_timestamps: null,
  last_timestamps: null,
  timestamps: ['2026-08-20T10:00:00'],
};

let generate: {
  mutate: ReturnType<typeof vi.fn>;
  isPending: boolean;
};

function setup(pluginNames = ['timer', 'cron']) {
  const getConfig = vi.fn(() => CONFIGS);

  renderWithProviders(
    <ProjectNameProvider initialProjectName="web">
      <TimestampsHistogram
        pluginNames={pluginNames}
        getInputPluginsConfig={getConfig}
      />
    </ProjectNameProvider>
  );

  return getConfig;
}

beforeEach(() => {
  vi.clearAllMocks();

  generate = {
    mutate: vi.fn(
      (
        _variables: unknown,
        handlers?: { onSuccess?: (data: typeof RESULT) => void }
      ) => {
        handlers?.onSuccess?.(RESULT);
      }
    ),
    isPending: false,
  };

  vi.mocked(useGenerateTimestampsMutation).mockReturnValue(
    generate as unknown as ReturnType<typeof useGenerateTimestampsMutation>
  );
});

/**
 * The preview runs the input stage of a configuration that is only open
 * in the studio, so the configuration is read at the moment the run is
 * asked for rather than when the tool was drawn. Selecting a subset of
 * the plugins must narrow what is sent - and selecting nothing must
 * mean all of them rather than none.
 */
describe('TimestampsHistogram', () => {
  it('says nothing has run yet', () => {
    setup();

    expect(
      screen.getByText(/Configure the parameters and run/)
    ).toBeInTheDocument();
  });

  it('sends every plugin when none is picked out', async () => {
    const user = userEvent.setup();
    const getConfig = setup();

    await user.click(screen.getByRole('button', { name: 'Generate' }));

    expect(getConfig).toHaveBeenCalled();

    const sent = generate.mutate.mock.calls[0]?.[0] as {
      inputPluginsConfig: InputPluginsNamedConfig;
      name: string;
    };

    expect(sent.name).toBe('web');
    expect(sent.inputPluginsConfig).toHaveLength(2);
  });

  it('reports the distribution once a run came back', async () => {
    const user = userEvent.setup();
    setup();

    await user.click(screen.getByRole('button', { name: 'Generate' }));

    expect(await screen.findByText('Distribution')).toBeInTheDocument();
    expect(screen.getByText('5 total')).toBeInTheDocument();
  });

  it('sends the parameters it was given', async () => {
    const user = userEvent.setup();
    setup();

    const count = screen.getByRole('textbox', { name: /Count/ });
    await user.clear(count);
    await user.type(count, '20');
    await user.click(screen.getByRole('button', { name: 'Generate' }));

    const sent = generate.mutate.mock.calls[0]?.[0] as { size: number };

    expect(sent.size).toBe(20);
  });

  it('refuses a time span it cannot read', async () => {
    const user = userEvent.setup();
    setup();

    await user.type(screen.getByRole('textbox', { name: /Time span/ }), 'soon');

    expect(await screen.findByText('Invalid span expression')).toBeVisible();
  });

  it('accepts a span expression and sends it', async () => {
    const user = userEvent.setup();
    setup();

    await user.type(screen.getByRole('textbox', { name: /Time span/ }), '5m');
    await user.click(screen.getByRole('button', { name: 'Generate' }));

    await waitFor(() => expect(generate.mutate).toHaveBeenCalled());

    const sent = generate.mutate.mock.calls[0]?.[0] as { span: string | null };

    expect(sent.span).toBe('5m');
  });

  it('sends no span at all when the field is left empty', async () => {
    const user = userEvent.setup();
    setup();

    await user.click(screen.getByRole('button', { name: 'Generate' }));

    const sent = generate.mutate.mock.calls[0]?.[0] as { span: string | null };

    expect(sent.span).toBeNull();
  });

  it('shows the run in flight while the request is out', () => {
    generate.isPending = true;
    setup();

    expect(screen.getByRole('button', { name: 'Generate' })).toHaveAttribute(
      'data-loading',
      'true'
    );
  });
});
