import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import { Navbar } from './index';
import { renderWithProviders } from '@/test/render';

function renderNavbar(onNavigate?: () => void): void {
  renderWithProviders(
    <MemoryRouter>
      <Navbar onNavigate={onNavigate} />
    </MemoryRouter>
  );
}

describe('Navbar', () => {
  it('reports every internal navigation so the caller can close it', async () => {
    const onNavigate = vi.fn();
    const user = userEvent.setup();
    renderNavbar(onNavigate);

    await user.click(screen.getByText('Instances'));
    expect(onNavigate).toHaveBeenCalledTimes(1);

    await user.click(screen.getByText('Home'));
    expect(onNavigate).toHaveBeenCalledTimes(2);

    await user.click(screen.getByText('Settings'));
    expect(onNavigate).toHaveBeenCalledTimes(3);
  });

  it('stays put on links that leave the app', async () => {
    const onNavigate = vi.fn();
    const user = userEvent.setup();
    renderNavbar(onNavigate);

    await user.click(screen.getByText('Documentation'));
    expect(onNavigate).not.toHaveBeenCalled();
  });

  it('renders without a navigation callback', async () => {
    const user = userEvent.setup();
    renderNavbar();

    await user.click(screen.getByText('Instances'));
    expect(screen.getByText('Instances')).toBeInTheDocument();
  });
});
