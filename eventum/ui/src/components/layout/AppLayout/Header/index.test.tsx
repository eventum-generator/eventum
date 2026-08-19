import { ModalsProvider } from '@mantine/modals';
import { screen } from '@testing-library/react';
import userEvent, { UserEvent } from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import { Header } from './index';
import { renderWithProviders } from '@/test/render';

interface Handlers {
  onMenuClick: () => void;
  onMobileMenuClick: () => void;
  onOpenHighlights?: () => void;
}

function renderHeader(handlers: Handlers): void {
  renderWithProviders(
    <MemoryRouter>
      <ModalsProvider>
        <Header username="eventum" onSignOut={vi.fn()} {...handlers} />
      </ModalsProvider>
    </MemoryRouter>
  );
}

/** Open the user menu, which holds the application entries. Targeted by
 *  text: jsdom cannot compute the accessible name of the target, whose
 *  label is assembled from several nodes. */
async function openUserMenu(user: UserEvent): Promise<void> {
  await user.click(screen.getByText('eventum').closest('button')!);
}

/** Both burgers are always in the document - which one the user can reach is
 *  decided by the media query behind these Mantine classes, and jsdom applies
 *  no stylesheet to hide the other. */
function burgers(): {
  desktop: Element | undefined;
  mobile: Element | undefined;
} {
  const all = [...document.querySelectorAll('button')];

  return {
    desktop: all.find((el) => el.className.includes('visible-from-sm')),
    mobile: all.find((el) => el.className.includes('hidden-from-sm')),
  };
}

describe('Header', () => {
  it('gives each navbar mode its own burger', () => {
    renderHeader({ onMenuClick: vi.fn(), onMobileMenuClick: vi.fn() });

    const { desktop, mobile } = burgers();
    expect(desktop).toBeDefined();
    expect(mobile).toBeDefined();
    expect(desktop).not.toBe(mobile);
  });

  it('toggles the desktop column from the wide burger', async () => {
    const onMenuClick = vi.fn();
    const onMobileMenuClick = vi.fn();
    const user = userEvent.setup();
    renderHeader({ onMenuClick, onMobileMenuClick });

    await user.click(burgers().desktop!);

    expect(onMenuClick).toHaveBeenCalledTimes(1);
    expect(onMobileMenuClick).not.toHaveBeenCalled();
  });

  it('toggles the mobile overlay from the narrow burger', async () => {
    const onMenuClick = vi.fn();
    const onMobileMenuClick = vi.fn();
    const user = userEvent.setup();
    renderHeader({ onMenuClick, onMobileMenuClick });

    await user.click(burgers().mobile!);

    expect(onMobileMenuClick).toHaveBeenCalledTimes(1);
    expect(onMenuClick).not.toHaveBeenCalled();
  });

  it('opens the release panels from the user menu', async () => {
    const onOpenHighlights = vi.fn();
    const user = userEvent.setup();
    renderHeader({
      onMenuClick: vi.fn(),
      onMobileMenuClick: vi.fn(),
      onOpenHighlights,
    });

    await openUserMenu(user);
    await user.click(await screen.findByText("What's new"));

    expect(onOpenHighlights).toHaveBeenCalledTimes(1);
  });

  it('offers no release panels on an instance that has none', async () => {
    const user = userEvent.setup();
    renderHeader({ onMenuClick: vi.fn(), onMobileMenuClick: vi.fn() });

    await openUserMenu(user);

    expect(await screen.findByText('About')).toBeInTheDocument();
    expect(screen.queryByText("What's new")).not.toBeInTheDocument();
  });
});
