import { ModalsProvider } from '@mantine/modals';
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { KeyValueTable, KeyValueTableProps } from './KeyValueTable';
import { renderWithProviders } from '@/test/render';

function setup(overrides: Partial<KeyValueTableProps> = {}) {
  const handlers = {
    onRefetch: vi.fn(),
    onUpdateKey: vi.fn(),
    onDeleteKey: vi.fn(),
    onAddKey: vi.fn(),
    onClear: vi.fn(),
  };

  renderWithProviders(
    <ModalsProvider>
      <KeyValueTable
        data={{ counter: 1, host: 'web-01', enabled: true }}
        isLoading={false}
        isError={false}
        error={null}
        isSuccess
        title="Shared state"
        {...handlers}
        {...overrides}
      />
    </ModalsProvider>
  );

  return handlers;
}

function rowKeys(): string[] {
  const rows = screen.getAllByRole('row').slice(1);

  return rows.map((row) => row.querySelectorAll('td')[0]?.textContent ?? '');
}

/**
 * The state tables show what a generator put in its state, of any JSON
 * shape and of any size. Everything below is what keeps such a table
 * readable: one stable order, a search that also looks at the values,
 * and paging once there are more keys than a screen holds.
 */
describe('KeyValueTable', () => {
  it('orders the keys by name, whatever order they arrived in', () => {
    setup({ data: { zeta: 1, alpha: 2, mid: 3 } });

    expect(rowKeys()).toEqual(['alpha', 'mid', 'zeta']);
  });

  it('counts the keys it holds', () => {
    setup();

    expect(screen.getByText('3 keys')).toBeInTheDocument();
  });

  it('counts a single key in the singular', () => {
    setup({ data: { only: 1 } });

    expect(screen.getByText('1 key')).toBeInTheDocument();
  });

  it('says so when the state is empty', () => {
    setup({ data: {}, emptyMessage: 'Nothing here' });

    expect(screen.getByText('Nothing here')).toBeInTheDocument();
  });

  it('reports a failure with its message', () => {
    setup({
      isSuccess: false,
      isError: true,
      error: new Error('no connection'),
      errorTitle: 'Failed to read',
    });

    expect(screen.getByText('Failed to read')).toBeInTheDocument();
    expect(screen.getByText(/no connection/)).toBeInTheDocument();
  });

  it('searches the values as well as the keys', async () => {
    const user = userEvent.setup();
    setup();

    await user.type(
      screen.getByPlaceholderText('Search keys or values...'),
      'web-01'
    );

    expect(rowKeys()).toEqual(['host']);
  });

  it('finds nothing for a search that matches neither', async () => {
    const user = userEvent.setup();
    setup();

    await user.type(
      screen.getByPlaceholderText('Search keys or values...'),
      'absent'
    );

    expect(rowKeys()).toEqual([]);
  });

  it('shows one page of keys at a time', () => {
    const data = Object.fromEntries(
      Array.from({ length: 25 }, (_, index) => [
        `key-${String(index).padStart(2, '0')}`,
        index,
      ])
    );

    setup({ data });

    expect(rowKeys()).toHaveLength(20);
    expect(screen.getByText('25 keys')).toBeInTheDocument();
  });

  it('shows the rest on the next page', async () => {
    const user = userEvent.setup();
    const data = Object.fromEntries(
      Array.from({ length: 25 }, (_, index) => [
        `key-${String(index).padStart(2, '0')}`,
        index,
      ])
    );

    setup({ data });

    await user.click(screen.getByRole('button', { name: '2' }));

    expect(rowKeys()).toHaveLength(5);
  });

  it('refreshes when asked', async () => {
    const user = userEvent.setup();
    const handlers = setup();

    await user.click(screen.getByRole('button', { name: 'Refresh' }));

    expect(handlers.onRefetch).toHaveBeenCalledTimes(1);
  });

  /**
   * Clearing throws away everything the generator accumulated, so it is
   * confirmed first - and offering it over an empty state would confirm
   * nothing.
   */
  it('confirms before clearing', async () => {
    const user = userEvent.setup();
    const handlers = setup();

    await user.click(screen.getByRole('button', { name: 'Clear all' }));

    const dialog = await screen.findByRole('dialog');
    expect(dialog).toHaveTextContent('all 3 keys');

    await user.click(within(dialog).getByRole('button', { name: 'Clear all' }));

    expect(handlers.onClear).toHaveBeenCalledTimes(1);
  });

  it('keeps the state when the confirmation is dismissed', async () => {
    const user = userEvent.setup();
    const handlers = setup();

    await user.click(screen.getByRole('button', { name: 'Clear all' }));
    await user.click(
      within(await screen.findByRole('dialog')).getByRole('button', {
        name: 'Cancel',
      })
    );

    expect(handlers.onClear).not.toHaveBeenCalled();
  });

  it('offers nothing to clear over an empty state', () => {
    setup({ data: {} });

    expect(screen.getByRole('button', { name: 'Clear all' })).toBeDisabled();
  });

  it('offers no keys to add before the state has been read', () => {
    setup({ isSuccess: false, isLoading: true });

    expect(screen.getByRole('button', { name: 'Add key' })).toBeDisabled();
  });
});
