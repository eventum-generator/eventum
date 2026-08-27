import { screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { InstanceBadges } from './InstanceBadges';
import { useGenerators } from '@/api/hooks/useGenerators';
import { GeneratorsInfo } from '@/api/routes/generators/schemas';
import { renderWithProviders } from '@/test/render';

vi.mock('@/api/hooks/useGenerators');

const IDLE = {
  is_initializing: false,
  is_running: false,
  is_ended_up: false,
  is_ended_up_successfully: false,
  is_stopping: false,
};

function generators(running: string[], all: string[]): GeneratorsInfo {
  return all.map((id) => ({
    id,
    path: `/p/${id}`,
    status: { ...IDLE, is_running: running.includes(id) },
    start_time: null,
  }));
}

function setup(
  ids: string[],
  props: Partial<{ moreTo: string; max: number; emptyText: string }> = {},
  running: string[] = []
) {
  vi.mocked(useGenerators).mockReturnValue({
    data: generators(running, ids),
  } as ReturnType<typeof useGenerators>);

  renderWithProviders(
    <MemoryRouter>
      <InstanceBadges ids={ids} {...props} />
    </MemoryRouter>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

/**
 * A table row has room for a few instance chips, so the rest collapse
 * into a counter. The counter is where the information would otherwise
 * be lost: it lights up when something hidden behind it is running, so
 * a row never looks idle while one of its instances is not.
 */
describe('InstanceBadges', () => {
  it('links every chip to its instance', () => {
    setup(['web', 'db']);

    expect(screen.getByRole('link', { name: /web/ })).toHaveAttribute(
      'href',
      '/instances/web'
    );
    expect(screen.getByRole('link', { name: /db/ })).toHaveAttribute(
      'href',
      '/instances/db'
    );
  });

  it('marks an empty list rather than drawing nothing', () => {
    setup([], { emptyText: 'Not used' });

    expect(screen.getByText('Not used')).toBeInTheDocument();
  });

  it('shows up to three chips before collapsing the rest', () => {
    setup(['a', 'b', 'c', 'd', 'e']);

    expect(screen.getByText('a')).toBeInTheDocument();
    expect(screen.getByText('c')).toBeInTheDocument();
    expect(screen.queryByText('d')).not.toBeInTheDocument();
    expect(screen.getByText('+2')).toBeInTheDocument();
  });

  it('collapses at the count it is given', () => {
    setup(['a', 'b', 'c'], { max: 1 });

    expect(screen.getByText('a')).toBeInTheDocument();
    expect(screen.getByText('+2')).toBeInTheDocument();
  });

  it('collapses nothing when everything fits', () => {
    setup(['a', 'b']);

    expect(screen.queryByText(/^\+/)).not.toBeInTheDocument();
  });

  it('lights the counter when a hidden instance is running', () => {
    setup(['a', 'b', 'c', 'd'], {}, ['d']);

    const counter = screen.getByText('+1').closest('.ev-chip-more');

    expect(counter?.querySelector('.ev-status-dot')).not.toBeNull();
  });

  it('leaves the counter dark when nothing hidden is running', () => {
    setup(['a', 'b', 'c', 'd'], {}, ['a']);

    const counter = screen.getByText('+1').closest('.ev-chip-more');

    expect(counter?.querySelector('.ev-status-dot')).toBeNull();
  });

  it('makes the counter a link only when given somewhere to go', () => {
    setup(['a', 'b', 'c', 'd'], { moreTo: '/instances?project=web' });

    expect(screen.getByRole('link', { name: '+1' })).toHaveAttribute(
      'href',
      '/instances?project=web'
    );
  });

  it('leaves the counter static without a destination', () => {
    setup(['a', 'b', 'c', 'd']);

    expect(screen.queryByRole('link', { name: '+1' })).not.toBeInTheDocument();
    expect(screen.getByText('+1')).toBeInTheDocument();
  });

  it('draws the chips before any status has been read', () => {
    vi.mocked(useGenerators).mockReturnValue({
      data: undefined,
    } as ReturnType<typeof useGenerators>);

    renderWithProviders(
      <MemoryRouter>
        <InstanceBadges ids={['web']} />
      </MemoryRouter>
    );

    expect(screen.getByRole('link', { name: /web/ })).toBeInTheDocument();
  });
});
