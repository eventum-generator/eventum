import { fireEvent, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { FC } from 'react';
import { describe, expect, it, vi } from 'vitest';

import { ReleaseHighlightsModal } from './index';
import { Release } from '@/releases';
import { renderWithProviders } from '@/test/render';

const Scene: FC = () => <svg data-testid="scene" />;

const RELEASE: Release = {
  version: '2.8.0',
  changelogHref: 'https://example.test/changelog/2.8.0',
  highlights: [
    {
      id: 'first',
      title: 'First change',
      body: 'What the first change is.',
      scene: Scene,
      docsHref: 'https://example.test/docs/first',
    },
    {
      id: 'second',
      title: 'Second change',
      body: 'What the second change is.',
      scene: Scene,
    },
    {
      id: 'third',
      title: 'Third change',
      body: 'What the third change is.',
      scene: Scene,
    },
  ],
};

function renderReel(onClose = vi.fn()) {
  const view = renderWithProviders(
    <ReleaseHighlightsModal release={RELEASE} opened onClose={onClose} />
  );

  return { onClose, view, user: userEvent.setup() };
}

describe('ReleaseHighlightsModal', () => {
  it('opens on the first panel, illustration included', () => {
    renderReel();

    expect(screen.getByText('First change')).toBeInTheDocument();
    expect(screen.getByTestId('scene')).toBeInTheDocument();
    expect(screen.queryByText('Second change')).not.toBeInTheDocument();
    expect(screen.getByRole('progressbar')).toHaveAttribute(
      'aria-valuenow',
      '1'
    );
    expect(screen.getByRole('button', { name: 'Back' })).toBeDisabled();
  });

  it('pages forward and back with the buttons', async () => {
    const { user } = renderReel();

    await user.click(screen.getByRole('button', { name: /Next/ }));

    expect(screen.getByText('Second change')).toBeInTheDocument();
    expect(screen.getByRole('progressbar')).toHaveAttribute(
      'aria-valuenow',
      '2'
    );
    await user.click(screen.getByRole('button', { name: /Back/ }));

    expect(screen.getByText('First change')).toBeInTheDocument();
  });

  it('pages with the arrow keys', async () => {
    const { user } = renderReel();

    await user.keyboard('{ArrowRight}');
    expect(screen.getByText('Second change')).toBeInTheDocument();

    await user.keyboard('{ArrowLeft}');
    expect(screen.getByText('First change')).toBeInTheDocument();
  });

  it('stops at the ends instead of wrapping around', async () => {
    const { user } = renderReel();

    await user.keyboard('{ArrowLeft}');
    expect(screen.getByText('First change')).toBeInTheDocument();

    await user.keyboard('{ArrowRight}{ArrowRight}{ArrowRight}');
    expect(screen.getByText('Third change')).toBeInTheDocument();
  });

  it('offers the changelog and closes on the last panel', async () => {
    const { user, onClose } = renderReel();

    expect(
      screen.queryByRole('link', { name: 'Full changelog' })
    ).not.toBeInTheDocument();

    await user.keyboard('{ArrowRight}{ArrowRight}');

    expect(
      screen.getByRole('link', { name: 'Full changelog' })
    ).toHaveAttribute('href', RELEASE.changelogHref);
    await user.click(screen.getByRole('button', { name: 'Done' }));

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('jumps to any panel from the dots', async () => {
    const { user, onClose } = renderReel();

    await user.click(screen.getByRole('button', { name: 'Panel 3' }));

    expect(screen.getByText('Third change')).toBeInTheDocument();
    expect(
      screen.getByRole('link', { name: 'Full changelog' })
    ).toBeInTheDocument();
    expect(onClose).not.toHaveBeenCalled();

    await user.click(screen.getByRole('button', { name: 'Panel 1' }));

    expect(screen.getByText('First change')).toBeInTheDocument();
  });

  it('starts from the first panel every time it is opened', async () => {
    const onClose = vi.fn();
    const { view, user } = renderReel(onClose);

    await user.click(screen.getByRole('button', { name: /Next/ }));
    expect(screen.getByText('Second change')).toBeInTheDocument();

    view.rerender(
      <ReleaseHighlightsModal
        release={RELEASE}
        opened={false}
        onClose={onClose}
      />
    );
    view.rerender(
      <ReleaseHighlightsModal release={RELEASE} opened onClose={onClose} />
    );

    expect(screen.getByText('First change')).toBeInTheDocument();
  });

  it('pages on a swipe, and not on a mouse selecting the text', () => {
    renderReel();

    const body = document.querySelector('.ev-reel-stage')!;

    fireEvent.pointerDown(body, { pointerType: 'touch', clientX: 300 });
    fireEvent.pointerUp(body, { pointerType: 'touch', clientX: 200 });
    expect(screen.getByText('Second change')).toBeInTheDocument();

    fireEvent.pointerDown(body, { pointerType: 'touch', clientX: 200 });
    fireEvent.pointerUp(body, { pointerType: 'touch', clientX: 300 });
    expect(screen.getByText('First change')).toBeInTheDocument();

    fireEvent.pointerDown(body, { pointerType: 'mouse', clientX: 300 });
    fireEvent.pointerUp(body, { pointerType: 'mouse', clientX: 200 });
    expect(screen.getByText('First change')).toBeInTheDocument();
  });

  // Reached by text: computing the accessible name of a link walks the
  // pseudo-elements of the card, which jsdom cannot resolve.
  it('links a panel to its documentation', () => {
    renderReel();

    expect(screen.getByText('Learn more').closest('a')).toHaveAttribute(
      'href',
      'https://example.test/docs/first'
    );
  });

  it('draws nothing for an instance with no panels', () => {
    renderWithProviders(
      <ReleaseHighlightsModal release={undefined} opened onClose={vi.fn()} />
    );

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });
});
