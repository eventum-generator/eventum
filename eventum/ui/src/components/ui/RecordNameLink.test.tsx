import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { RecordNameLink } from './RecordNameLink';
import { renderWithProviders } from '@/test/render';

function setup() {
  renderWithProviders(
    <MemoryRouter initialEntries={['/instances']}>
      <Routes>
        <Route
          path="/instances"
          element={<RecordNameLink to="/instances/web">web</RecordNameLink>}
        />
        <Route path="/instances/web" element={<p>Instance page</p>} />
      </Routes>
    </MemoryRouter>
  );
}

/** Pretend the user has a selection inside the given element. */
function selectInside(element: Node) {
  vi.spyOn(globalThis, 'getSelection').mockReturnValue({
    isCollapsed: false,
    anchorNode: element,
  } as unknown as Selection);
}

afterEach(() => {
  vi.restoreAllMocks();
});

/**
 * A record name is both a link and a value the user may want to copy.
 * Selecting the text ends in a click, so a click that finished a
 * selection must not navigate - otherwise the name cannot be copied at
 * all.
 */
describe('RecordNameLink', () => {
  it('links to the record', () => {
    setup();

    expect(screen.getByRole('link', { name: 'web' })).toHaveAttribute(
      'href',
      '/instances/web'
    );
  });

  it('opens the record on a plain click', async () => {
    const user = userEvent.setup();
    setup();

    await user.click(screen.getByRole('link', { name: 'web' }));

    expect(screen.getByText('Instance page')).toBeInTheDocument();
  });

  it('does not open it when the click ended a selection of the name', async () => {
    const user = userEvent.setup();
    setup();

    const link = screen.getByRole('link', { name: 'web' });
    selectInside(link);

    await user.click(link);

    expect(screen.queryByText('Instance page')).not.toBeInTheDocument();
  });

  it('opens it when the selection is somewhere else', async () => {
    const user = userEvent.setup();
    setup();

    selectInside(document.body);

    await user.click(screen.getByRole('link', { name: 'web' }));

    expect(screen.getByText('Instance page')).toBeInTheDocument();
  });

  it('opens it when the selection is empty', async () => {
    const user = userEvent.setup();
    setup();

    const link = screen.getByRole('link', { name: 'web' });
    vi.spyOn(globalThis, 'getSelection').mockReturnValue({
      isCollapsed: true,
      anchorNode: link,
    } as unknown as Selection);

    await user.click(link);

    expect(screen.getByText('Instance page')).toBeInTheDocument();
  });
});
