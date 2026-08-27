import { screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { StatusRail } from './StatusRail';
import {
  GeneratorStats,
  GeneratorStatus,
  GeneratorsInfo,
} from '@/api/routes/generators/schemas';
import { renderWithProviders } from '@/test/render';

const IDLE: GeneratorStatus = {
  is_initializing: false,
  is_running: false,
  is_ended_up: false,
  is_ended_up_successfully: false,
  is_stopping: false,
};

function instance(
  id: string,
  overrides: { running?: boolean; startTime?: string | null } = {}
) {
  return {
    id,
    path: `${id}/generator.yml`,
    status: { ...IDLE, is_running: overrides.running ?? false },
    start_time: overrides.startTime ?? null,
  };
}

function stats(id: string, uptime: number): GeneratorStats {
  return { id, uptime } as GeneratorStats;
}

function setup(
  generators: GeneratorsInfo = [instance('web')],
  generatorsStats: GeneratorStats[] = []
) {
  renderWithProviders(
    <MemoryRouter>
      <StatusRail generators={generators} generatorsStats={generatorsStats} />
    </MemoryRouter>
  );
}

/**
 * The rail is the answer the home page gives at a glance: how much is
 * running and what ran last. It lists the five most recent instances, so
 * an instance that has just been started has to be among them however
 * many came before it.
 */
describe('StatusRail', () => {
  it('counts the instances of the workspace', () => {
    setup([instance('web'), instance('api')]);

    // The buckets of the summary carry figures of their own, so the
    // total is read from the group it sits in with its word.
    const word = screen.getByText('instances');

    expect(word.parentElement).toHaveTextContent(/^2\s*instances$/);
  });

  it('names one instance in the singular', () => {
    setup([instance('web')]);

    expect(screen.getByText('instance')).toBeInTheDocument();
  });

  it('says there is nothing to show yet', () => {
    setup([]);

    expect(screen.getByText('No instances yet.')).toBeInTheDocument();
  });

  it('names each instance with the project it runs', () => {
    setup([instance('web-live')]);

    // The row carries the instance and, under it, the project read off
    // the configuration path - by its own name rather than the whole
    // directory.
    const row = screen.getByRole('link', { name: /web-live/ });

    expect(row).toHaveTextContent('web-live');
    expect(row).toHaveTextContent('web-live');
  });

  it('names the project of a configuration outside the workspace by its directory', () => {
    setup([
      {
        ...instance('web'),
        path: '/opt/eventum/legacy/generator.yml',
      },
    ]);

    expect(screen.getByText('legacy')).toBeInTheDocument();
  });

  it('adds how long a running instance has been up', () => {
    setup([instance('web', { running: true })], [stats('web', 3600)]);

    expect(screen.getByText(/up /)).toBeInTheDocument();
  });

  it('says nothing about uptime for an instance at rest', () => {
    setup([instance('web')], [stats('web', 3600)]);

    expect(screen.queryByText(/up /)).toBeNull();
  });

  it('lists the five most recent instances, newest first', () => {
    setup(
      Array.from({ length: 7 }, (_, i) =>
        instance(`inst-${i}`, {
          startTime: `2026-01-0${i + 1}T00:00:00+00:00`,
        })
      )
    );

    const listed = screen
      .getAllByRole('link')
      .map((link) => link.getAttribute('href'))
      .filter((href) => href?.startsWith('/instances/'));

    expect(listed).toEqual([
      '/instances/inst-6',
      '/instances/inst-5',
      '/instances/inst-4',
      '/instances/inst-3',
      '/instances/inst-2',
    ]);
  });

  it('opens the instance a row stands for', () => {
    setup([instance('web')]);

    expect(screen.getByRole('link', { name: /web/ })).toHaveAttribute(
      'href',
      '/instances/web'
    );
  });

  it('offers the monitoring of the whole fleet', () => {
    setup();

    expect(
      screen.getByRole('link', { name: /Monitoring|Live/ })
    ).toHaveAttribute('href', '/monitoring');
  });
});
