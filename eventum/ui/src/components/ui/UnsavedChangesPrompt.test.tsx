import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Link, RouterProvider, createMemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { UnsavedChangesPrompt } from './UnsavedChangesPrompt';
import { renderWithProviders } from '@/test/render';

// The prompt blocks navigation, which only a data router can be asked
// to do - a plain memory router has nothing to block with.
function setup(when: boolean, message?: string) {
  const router = createMemoryRouter(
    [
      {
        path: '/project',
        element: (
          <>
            <UnsavedChangesPrompt when={when} message={message} />
            <Link to="/projects">Back to projects</Link>
          </>
        ),
      },
      { path: '/projects', element: <p>Projects page</p> },
    ],
    { initialEntries: ['/project'] }
  );

  renderWithProviders(<RouterProvider router={router} />);
}

/**
 * The prompt is the only thing between an unsaved edit and losing it, so
 * what matters is that it appears exactly when there is something to
 * lose, and that dismissing it keeps the user where they were.
 */
describe('UnsavedChangesPrompt', () => {
  it('lets navigation through when nothing is unsaved', async () => {
    const user = userEvent.setup();
    setup(false);

    await user.click(screen.getByRole('link', { name: 'Back to projects' }));

    expect(await screen.findByText('Projects page')).toBeInTheDocument();
  });

  it('stops navigation while an edit is unsaved', async () => {
    const user = userEvent.setup();
    setup(true);

    await user.click(screen.getByRole('link', { name: 'Back to projects' }));

    expect(await screen.findByRole('dialog')).toBeInTheDocument();
    expect(screen.queryByText('Projects page')).not.toBeInTheDocument();
  });

  it('keeps the user on the page when they choose to stay', async () => {
    const user = userEvent.setup();
    setup(true);

    await user.click(screen.getByRole('link', { name: 'Back to projects' }));
    await user.click(await screen.findByRole('button', { name: 'Stay' }));

    expect(screen.queryByText('Projects page')).not.toBeInTheDocument();
    expect(
      screen.getByRole('link', { name: 'Back to projects' })
    ).toBeInTheDocument();
  });

  it('lets the edit go when they choose to leave', async () => {
    const user = userEvent.setup();
    setup(true);

    await user.click(screen.getByRole('link', { name: 'Back to projects' }));
    await user.click(await screen.findByRole('button', { name: 'Leave' }));

    expect(await screen.findByText('Projects page')).toBeInTheDocument();
  });

  it('says what is at stake in its own words when given them', async () => {
    const user = userEvent.setup();
    setup(true, 'The template is not saved.');

    await user.click(screen.getByRole('link', { name: 'Back to projects' }));

    expect(
      await screen.findByText('The template is not saved.')
    ).toBeInTheDocument();
  });

  it('draws no dialog until navigation is attempted', () => {
    setup(true);

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });
});
