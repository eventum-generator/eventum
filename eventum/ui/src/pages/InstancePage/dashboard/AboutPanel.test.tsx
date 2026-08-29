import { screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { AboutPanel } from './AboutPanel';
import { useGenerators } from '@/api/hooks/useGenerators';
import {
  GeneratorParameters,
  GeneratorsInfo,
} from '@/api/routes/generators/schemas';
import { renderWithProviders } from '@/test/render';

vi.mock('@/api/hooks/useGenerators');

const IDLE = {
  is_initializing: false,
  is_running: false,
  is_ended_up: false,
  is_ended_up_successfully: false,
  is_stopping: false,
};

const PARAMS = {
  id: 'web',
  path: 'web/generator.yml',
} as GeneratorParameters;

function setup(
  overrides: {
    params?: GeneratorParameters;
    liveMode?: boolean;
    autostart?: boolean;
    startTime?: string | null;
  } = {}
) {
  const instances: GeneratorsInfo = [
    {
      id: 'web',
      path: PARAMS.path,
      status: IDLE,
      start_time: overrides.startTime ?? null,
    },
  ];

  vi.mocked(useGenerators).mockReturnValue({
    data: instances,
  } as unknown as ReturnType<typeof useGenerators>);

  renderWithProviders(
    <MemoryRouter>
      <AboutPanel
        instanceId="web"
        generatorParams={overrides.params ?? PARAMS}
        liveMode={overrides.liveMode ?? true}
        autostart={overrides.autostart ?? false}
      />
    </MemoryRouter>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

/**
 * The panel answers what this instance is: which project it runs, in
 * which mode, and whether it has ever run. The project is derived from
 * the configuration path rather than stored, so it is the one figure
 * that can be wrong without anything else noticing.
 */
describe('AboutPanel', () => {
  it('names the project from the configuration path', () => {
    setup();

    expect(screen.getByText('web')).toBeInTheDocument();
  });

  it('links the project by its name', () => {
    setup();

    expect(screen.getByRole('link')).toHaveAttribute('href', '/projects/web');
  });

  // A generator can be registered from anywhere on the host, and the
  // backend then reports the path it was registered with. There is no
  // project page for it, so the path is shown instead of a link that
  // would land on a project route that resolves to nothing.
  it('shows the path of a configuration outside the workspace', () => {
    setup({
      params: {
        ...PARAMS,
        path: '/opt/eventum/web/generator.yml',
      } as GeneratorParameters,
    });

    expect(
      screen.getByText('/opt/eventum/web/generator.yml')
    ).toBeInTheDocument();
    expect(screen.queryByRole('link')).toBeNull();
  });

  it('names the mode the instance runs in', () => {
    setup({ liveMode: true });

    expect(screen.getByText('Live')).toBeInTheDocument();
  });

  it('names the other mode as such', () => {
    setup({ liveMode: false });

    expect(screen.getByText('Sample')).toBeInTheDocument();
  });

  it.each([
    [true, 'On'],
    [false, 'Off'],
  ])('reports autostart %s as %s', (autostart, expected) => {
    setup({ autostart });

    expect(screen.getByText(expected)).toBeInTheDocument();
  });

  it('falls back to UTC when the instance names no timezone', () => {
    setup();

    expect(screen.getByText('UTC')).toBeInTheDocument();
  });

  it('names the timezone the instance was given', () => {
    setup({
      params: { ...PARAMS, timezone: 'Europe/Moscow' } as GeneratorParameters,
    });

    expect(screen.getByText('Europe/Moscow')).toBeInTheDocument();
  });

  it('says an instance has never run rather than showing nothing', () => {
    setup({ startTime: null });

    expect(screen.getByText('Never')).toBeInTheDocument();
  });

  it('reports how long ago it last ran', () => {
    setup({ startTime: new Date(Date.now() - 3_600_000).toISOString() });

    expect(screen.getByText(/ago$/)).toBeInTheDocument();
  });
});
