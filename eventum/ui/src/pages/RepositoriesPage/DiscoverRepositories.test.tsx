import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { DiscoverRepositories } from './DiscoverRepositories';
import { useDiscoveredRepositories } from '@/api/hooks/useRepositories';
import {
  DiscoveredRepository,
  Discovery,
} from '@/api/routes/repositories/schemas';
import { renderWithProviders } from '@/test/render';

vi.mock('@/api/hooks/useRepositories');

function published(
  overrides: Partial<DiscoveredRepository> = {}
): DiscoveredRepository {
  return {
    name: 'content-packs',
    full_name: 'eventum-generator/content-packs',
    url: 'https://github.com/eventum-generator/content-packs.git',
    page_url: 'https://github.com/eventum-generator/content-packs',
    owner: 'eventum-generator',
    description: 'Official repository of generators for Eventum',
    topics: ['eventum-generators'],
    stars: 5,
    updated_at: '2026-07-31T09:00:00+00:00',
    license: 'Apache-2.0',
    archived: false,
    official: true,
    connected: false,
    ...overrides,
  } as DiscoveredRepository;
}

function discovery(
  entries: DiscoveredRepository[],
  totalCount = entries.length
): Discovery {
  return {
    topic: 'eventum-generators',
    // The words the listing was narrowed with, empty when it was not.
    query: '',
    entries,
    total_count: totalCount,
    refreshed_at: '2026-08-01T10:00:00+00:00',
    rate: { remaining: 9, reset_at: '2026-08-01T11:00:00+00:00' },
  } as Discovery;
}

interface Options {
  pages?: Discovery[];
  isLoading?: boolean;
  isError?: boolean;
  hasNextPage?: boolean;
  onConnect?: (repository: DiscoveredRepository) => void;
}

function setup(options: Options = {}) {
  const fetchNextPage = vi.fn();

  vi.mocked(useDiscoveredRepositories).mockReturnValue({
    data: options.pages === undefined ? undefined : { pages: options.pages },
    isLoading: options.isLoading ?? false,
    isError: options.isError ?? false,
    error: options.isError === true ? new Error('rate limited') : null,
    hasNextPage: options.hasNextPage ?? false,
    isFetchingNextPage: false,
    fetchNextPage,
  } as unknown as ReturnType<typeof useDiscoveredRepositories>);

  renderWithProviders(
    <DiscoverRepositories onConnect={options.onConnect ?? vi.fn()} />
  );

  return { user: userEvent.setup(), fetchNextPage };
}

beforeEach(() => {
  vi.clearAllMocks();
});

/**
 * The tab lists what is published under the topic, which is anyone's
 * repository. A generator carries templates and scripts that run on this
 * machine, so the page has to say that what it lists is not reviewed -
 * and it must not offer to connect what is connected already.
 */
describe('DiscoverRepositories', () => {
  it('says that what it lists is not reviewed', () => {
    setup({ pages: [discovery([published()])] });

    expect(
      screen.getByText('Community repositories are not reviewed')
    ).toBeInTheDocument();
    expect(screen.getByText(/executed on this machine/)).toBeInTheDocument();
  });

  it('lists what carries the topic', () => {
    setup({ pages: [discovery([published()])] });

    expect(
      screen.getByText('eventum-generator/content-packs')
    ).toBeInTheDocument();
    expect(screen.getByText('1 repository found')).toBeInTheDocument();
  });

  it('marks the official repository as such', () => {
    setup({ pages: [discovery([published()])] });

    expect(screen.getByText('official')).toBeInTheDocument();
  });

  it('names what a repository says about itself', () => {
    setup({ pages: [discovery([published()])] });

    expect(
      screen.getByText('Official repository of generators for Eventum')
    ).toBeInTheDocument();
    expect(screen.getByText('Apache-2.0')).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument();
  });

  it('hands over the repository that is being connected', async () => {
    const onConnect = vi.fn();
    const { user } = setup({
      pages: [discovery([published()])],
      onConnect,
    });

    await user.click(screen.getByRole('button', { name: 'Connect' }));

    expect(onConnect).toHaveBeenCalledWith(
      expect.objectContaining({ name: 'content-packs' })
    );
  });

  it('offers no second connection of what is connected', () => {
    setup({ pages: [discovery([published({ connected: true })])] });

    expect(screen.getByRole('button', { name: 'Connected' })).toBeDisabled();
  });

  it('reports a search it could not run', () => {
    setup({ isError: true });

    // The instance reaches GitHub for this, and its rate limit is the
    // usual reason - which the message carries.
    expect(
      screen.getByText('Failed to search published repositories')
    ).toBeInTheDocument();
  });

  it('says nothing carries the topic yet', () => {
    setup({ pages: [discovery([])] });

    expect(screen.getByText('Nothing published matches')).toBeInTheDocument();
    expect(
      screen.getByText('No repository carries the topic yet.')
    ).toBeInTheDocument();
  });

  it('says the words of the search matched nothing', () => {
    setup({ pages: [{ ...discovery([]), query: 'nginx' }] });

    expect(
      screen.getByText('No repository carrying the topic matches these words.')
    ).toBeInTheDocument();
  });

  it('reads the rest of a long listing on request', async () => {
    const { user, fetchNextPage } = setup({
      pages: [discovery([published()], 40)],
      hasNextPage: true,
    });

    await user.click(screen.getByRole('button', { name: 'Load more' }));

    expect(fetchNextPage).toHaveBeenCalledTimes(1);
  });

  it('says how much of a listing it could not reach', () => {
    setup({ pages: [discovery([published()], 40)], hasNextPage: false });

    // The search is answered a page at a time and the answer is capped,
    // so the page says so rather than looking complete.
    expect(
      screen.getByText(/The first 1 of 40 are listed/)
    ).toBeInTheDocument();
  });

  it('names the topic a repository is listed by', () => {
    setup({ pages: [discovery([published()])] });

    expect(screen.getByText('eventum-generators')).toBeInTheDocument();
    expect(
      screen.getByRole('link', { name: 'Publish your own' })
    ).toBeInTheDocument();
  });
});
